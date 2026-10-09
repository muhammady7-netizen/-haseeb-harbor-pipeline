import json
import operator
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, RootModel, field_validator

from ..models import StrictModel
from ..source_types import SourceCommand, SourceContext, SourceDataError

MAX_PDF_BYTES = 64 * 1024 * 1024
MAX_PDF_PAGES = 1_000
MAX_PDF_EXTRACTED_CHARS = 5_000_000
PDF_WORKER_TIMEOUT_SECONDS = 45
PDF_WORKER_MEMORY_BYTES = 768 * 1024 * 1024

# The worker writes exactly one result line prefixed with this marker. Anything
# else a library prints (PyMuPDF >= 1.28 prints a deprecation notice for
# ``import fitz``) is ignored by the parent instead of breaking the JSON parse.
_PDF_RESULT_MARKER = "@@RLWV-PDF-RESULT@@"

_PDF_TEXT_WORKER = r'''\
import json
import os
import resource
import sys

_RESULT_MARKER = "@@RLWV-PDF-RESULT@@"
# Library chatter goes to stderr; only the marked result line uses stdout.
_RESULT_STREAM = sys.stdout
sys.stdout = sys.stderr


# Typographic ligatures (U+FB00-FB06) come back as one code point from fonts
# that draw them (PyMuPDF's Story writer, many TeX and InDesign PDFs): "\ufb01lm"
# for "film". Readers see letters, so every text the worker returns is expanded.
_LIGATURES = {0xFB00: "ff", 0xFB01: "fi", 0xFB02: "fl", 0xFB03: "ffi", 0xFB04: "ffl", 0xFB05: "st", 0xFB06: "st"}


def plain(text):
    return (text or "").translate(_LIGATURES)


def emit(payload):
    _RESULT_STREAM.write(_RESULT_MARKER + json.dumps(payload, ensure_ascii=False) + "\n")
    _RESULT_STREAM.flush()


def set_limit(kind, value):
    soft, hard = resource.getrlimit(kind)
    bounded = value if hard == resource.RLIM_INFINITY else min(value, hard)
    if soft > bounded:
        resource.setrlimit(kind, (bounded, hard))
    resource.setrlimit(kind, (bounded, bounded))


try:
    # macOS exposes RLIMIT_AS but rejects lowering it; production grading is
    # Linux, where this is the hard parser-memory boundary.
    if sys.platform != "darwin":
        set_limit(resource.RLIMIT_AS, int(sys.argv[5]))
    set_limit(resource.RLIMIT_CPU, 30)
    set_limit(resource.RLIMIT_FSIZE, 0)
    set_limit(resource.RLIMIT_NOFILE, 64)
    set_limit(resource.RLIMIT_CORE, 0)
    try:
        import pymupdf as fitz  # pyright: ignore[reportMissingImports]
    except ImportError:
        import fitz  # pyright: ignore[reportMissingImports]  # PyMuPDF < 1.24.3

    path, mode = sys.argv[1], sys.argv[2]
    limit, aggregate_limit = int(sys.argv[3]), int(sys.argv[4])
    label_stem = sys.argv[6] if len(sys.argv) > 6 else ""
    if os.stat(path).st_size > 64 * 1024 * 1024:
        raise ValueError("PDF artifact exceeds the file-size limit")
    document = fitz.open(path)
    if not document.is_pdf or document.needs_pass or not len(document):
        raise ValueError("unsupported PDF document")
    if len(document) > 1000:
        raise ValueError("PDF page count exceeds limit")
    page_count = len(document)
    total_extracted = 0
    parts = []
    answers = []
    returned = 0
    truncated = False
    character_count = 0
    if mode == "blocks":
        blocks_out = []
        for page_index, page in enumerate(document):
            blocks = [b for b in page.get_text("blocks", sort=False) if len(b) <= 6 or b[6] == 0]
            for block_index, block in enumerate(blocks):
                text = plain(block[4])
                total_extracted += len(text)
                if total_extracted > aggregate_limit:
                    raise ValueError("PDF extractable text exceeds the supported limit")
                blocks_out.append([page_index + 1, block_index, text])
    design = None
    if mode == "blocks":
        design = {"blocks": blocks_out}
    elif mode == "meta":
        meta = document.metadata or {}
        design = {"page_count": page_count}
        for key in ("title", "author", "subject", "keywords", "creator", "producer"):
            design[key] = str(meta.get(key) or "").strip()[:limit or 500]
    elif mode == "fonts":
        import re as _re
        subset = _re.compile(r"^[A-Z]{6}\+")
        seen = {}
        unused = set()
        for page_index, page in enumerate(document):
            # Only fonts that draw text count: a generator may register a
            # font resource (ReportLab's Helvetica) that no text uses.
            used = set()
            for block in page.get_text("dict").get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if str(span.get("text") or "").strip():
                            used.add(subset.sub("", str(span.get("font") or "")))
            for entry in page.get_fonts(full=True):
                xref, ext, ftype, basefont = entry[0], entry[1], entry[2], entry[3]
                raw = str(basefont or entry[4] or "")
                name = subset.sub("", raw)
                if name not in used and str(entry[4] or "") not in used:
                    unused.add(name)
                    continue
                embedded = str(ext or "n/a") != "n/a" or ftype == "Type3"
                key = (name, ftype, embedded)
                if key not in seen:
                    if len(seen) >= 500:
                        continue
                    seen[key] = {"name": name, "type": str(ftype or ""), "embedded": embedded,
                                 "subset": raw != name, "pages": []}
                if page_index + 1 not in seen[key]["pages"] and len(seen[key]["pages"]) < 50:
                    seen[key]["pages"].append(page_index + 1)
        design = {"fonts": list(seen.values()),
                  "unused": sorted(unused - {f["name"] for f in seen.values()})[:100]}
    elif mode == "links":
        import re as _re
        url_re = _re.compile(r"(?i)^(?:https?://|www\.)[^\s]+")
        strip_chars = "()[]<>{}\"'.,;:!?"
        links, url_texts = [], []
        link_total = 0
        for page_index, page in enumerate(document):
            rects = []
            for link in page.get_links():
                uri = link.get("uri")
                if not uri:
                    continue
                link_total += 1
                rects.append(link.get("from"))
                if len(links) < 500:
                    links.append({"page": page_index + 1, "uri": str(uri)[:500]})
            for word in page.get_text("words", sort=False):
                token = plain(str(word[4])).strip(strip_chars)
                if not url_re.match(token):
                    continue
                box = fitz.Rect(word[:4])
                linked = any(r is not None and (box & r).get_area() > 0 for r in rects)
                if len(url_texts) < 500:
                    url_texts.append({"page": page_index + 1, "text": token[:500], "linked": linked})
        design = {"links": links, "link_count": link_total, "url_texts": url_texts}
    elif mode == "codepoints":
        chars = set(range(0x2070, 0x20A0)) | {0xB2, 0xB3, 0xB9}
        counts, samples = {}, []
        for page_index, page in enumerate(document):
            text = plain(page.get_text("text", sort=False))
            total_extracted += len(text)
            if total_extracted > aggregate_limit:
                raise ValueError("PDF extractable text exceeds the supported limit")
            for pos, ch in enumerate(text):
                if ord(ch) in chars:
                    counts[ch] = counts.get(ch, 0) + 1
                    if len(samples) < 20:
                        context = text[max(0, pos - 20):pos + 21].replace("\n", " ")
                        samples.append({"page": page_index + 1, "char": ch,
                                        "codepoint": "U+%04X" % ord(ch), "context": context})
        design = {"counts": counts, "samples": samples}
    elif mode == "tables":
        tables = []
        for page_index, page in enumerate(document):
            found = page.find_tables()
            for table in found.tables:
                rows = [[("" if cell is None else plain(str(cell))) for cell in row] for row in table.extract()]
                if len(tables) < 100:
                    tables.append({"page": page_index + 1, "rows": rows[:2000]})
        design = {"tables": tables}
    for page in document:
        if mode not in ("extract", "inspect", "answers"):
            continue
        # sort=False keeps each text block (column) whole in content-stream order;
        # sort=True interleaves side-by-side columns line by line.
        text = plain(page.get_text("text", sort=False))
        total_extracted += len(text)
        if total_extracted > aggregate_limit:
            raise ValueError("PDF extractable text exceeds the supported limit")
        if mode == "inspect":
            character_count += len(text.strip())
            continue
        if mode == "extract":
            text = text.strip()
            if not text:
                continue
            separator = 1 if parts else 0
            remaining = max(0, limit - returned - separator)
            if not remaining:
                truncated = True
                break
            bounded = text[:remaining]
            parts.append(bounded)
            returned += separator + len(bounded)
            if len(bounded) < len(text):
                truncated = True
                break
            continue
        for line in text.splitlines():
            if "=" not in line:
                continue
            answer = line.rsplit("=", 1)[-1].strip()
            separator = 1 if answers else 0
            remaining = max(0, limit - returned - separator)
            if not remaining:
                truncated = True
                break
            bounded = answer[:remaining]
            answers.append(bounded)
            returned += separator + len(bounded)
            if len(bounded) < len(answer):
                truncated = True
                break
        if truncated:
            break
    document.close()
    if design is not None:
        result = design
    elif mode == "inspect":
        result = {"page_count": page_count, "character_count": character_count}
    elif mode == "pages":
        result = {"page_count": page_count}
    elif mode == "extract":
        result = {"text": "\n".join(parts), "truncated": truncated}
    else:
        result = {"answers": answers, "truncated": truncated}
    emit({"ok": True, "result": result})
except BaseException as exc:
    try:
        emit({"ok": False, "error": type(exc).__name__ + ": " + str(exc)})
    except BaseException:
        pass
    raise SystemExit(2)
'''


def _run_pdf_text_worker(
    path: Path, mode: str, limit: int, label: str = ""
) -> dict[str, Any]:
    """Parse an untrusted PDF in a memory- and CPU-limited process."""
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise SourceDataError(f"could not inspect PDF {path.name}") from exc
    if size == 0:
        raise SourceDataError("PDF artifact is empty")
    if size > MAX_PDF_BYTES:
        raise SourceDataError(f"PDF artifact exceeds {MAX_PDF_BYTES} bytes")
    try:
        process = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                _PDF_TEXT_WORKER,
                str(path),
                mode,
                str(max(0, limit)),
                str(MAX_PDF_EXTRACTED_CHARS),
                str(PDF_WORKER_MEMORY_BYTES),
                label,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=PDF_WORKER_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SourceDataError("PDF text extraction exceeded its CPU-time budget") from exc
    if len(process.stdout) > MAX_PDF_EXTRACTED_CHARS * 4 + 1_000_000:
        raise SourceDataError("PDF text extraction returned excessive evidence")
    try:
        payload = _worker_payload(process.stdout)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise SourceDataError(
            "PDF text extraction failed inside its resource sandbox"
        ) from exc
    if process.returncode != 0 or not payload.get("ok"):
        detail = str(payload.get("error", "worker exited unexpectedly"))[:500]
        raise SourceDataError(f"malformed or excessive PDF text: {detail}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise SourceDataError("PDF text extraction returned malformed evidence")
    return result


def _worker_payload(stdout: str) -> dict[str, Any]:
    """Return the worker's marked result line, ignoring any other output."""
    lines = [
        line[len(_PDF_RESULT_MARKER):]
        for line in (stdout or "").splitlines()
        if line.startswith(_PDF_RESULT_MARKER)
    ]
    if len(lines) != 1:
        raise ValueError("PDF worker did not emit exactly one result line")
    payload = json.loads(lines[0])
    if not isinstance(payload, dict):
        raise ValueError("PDF worker result is not an object")
    return payload


class PdfExtractTextInput(StrictModel):
    """Input for pdf.extract_text.

    Attributes:
        path: Workspace-relative PDF path.
    """

    path: str

    @field_validator("path")
    @classmethod
    def require_pdf_extension(cls, value: str) -> str:
        """Requires the path to target a PDF file.

        Args:
            value: Workspace-relative path from verifier.json.

        Returns:
            The unchanged path when it has a PDF extension.

        Raises:
            ValueError: If the path does not end in ``.pdf``.
        """
        if Path(value).suffix.lower() != ".pdf":
            raise ValueError("pdf.extract_text requires a .pdf file")
        return value


class PdfExtractTextOutput(StrictModel):
    """Output from pdf.extract_text.

    Attributes:
        text: Extracted page text.
        truncated: Whether additional nonempty text was omitted by the evidence cap.
    """

    text: str
    truncated: bool = False


class ExtractText(SourceCommand[PdfExtractTextInput, PdfExtractTextOutput]):
    """Extracts text from PDF pages."""

    name = "extract_text"
    input_model = PdfExtractTextInput
    output_model = PdfExtractTextOutput

    def run(self, source_input: PdfExtractTextInput, context: SourceContext) -> PdfExtractTextOutput:
        """Runs PDF text extraction.

        Args:
            source_input: Validated PDF extraction input.
            context: Source runtime context.

        Returns:
            Extracted PDF text.
        """
        resolved = context.resolve_path(source_input.path)
        text, truncated = extract_pdf_text_bounded(
            resolved, context.max_content_chars
        )
        return PdfExtractTextOutput(text=text, truncated=truncated)


class PdfInspectDocumentInput(StrictModel):
    """Input for ``pdf.inspect_document``.

    Attributes:
        path: Workspace-relative PDF path.
    """

    path: str

    @field_validator("path")
    @classmethod
    def require_pdf_extension(cls, value: str) -> str:
        """Requires the path to target a PDF file.

        Args:
            value: Workspace-relative path from verifier.json.

        Returns:
            The unchanged path when it has a PDF extension.

        Raises:
            ValueError: If the path does not end in ``.pdf``.
        """
        if Path(value).suffix.lower() != ".pdf":
            raise ValueError("pdf.inspect_document requires a .pdf file")
        return value


class PdfInspectDocumentOutput(StrictModel):
    """PDF structure expressed as counts.

    Attributes:
        page_count: Pages in the document, which is what a prompt constraining
            a deliverable to "no more than two pages" actually states.
        character_count: Extractable text characters across every page. Not
            capped by the source content limit, because this command returns
            counts rather than the text itself.
        has_text: Whether any page yields extractable text. A scanned or
            image-only PDF reports False, which distinguishes "the model
            delivered an image" from "the content is wrong".
    """

    page_count: int
    character_count: int
    has_text: bool


class InspectDocument(SourceCommand[PdfInspectDocumentInput, PdfInspectDocumentOutput]):
    """Report a PDF's page count and whether it carries extractable text."""

    name = "inspect_document"
    input_model = PdfInspectDocumentInput
    output_model = PdfInspectDocumentOutput

    def run(
        self, source_input: PdfInspectDocumentInput, context: SourceContext
    ) -> PdfInspectDocumentOutput:
        """Runs PDF structure inspection.

        Args:
            source_input: Validated document inspection input.
            context: Source runtime context.

        Returns:
            PDF structure as counts.
        """
        resolved = context.resolve_path(source_input.path)
        return inspect_pdf_document(resolved)


def inspect_pdf_document(path: Path) -> PdfInspectDocumentOutput:
    """Reads a PDF's page count and extractable-text volume.

    Args:
        path: Resolved PDF file path.

    Returns:
        PDF structure as counts.
    """
    result = _run_pdf_text_worker(path, "inspect", 0)
    page_count = int(result["page_count"])
    character_count = int(result["character_count"])
    return PdfInspectDocumentOutput(
        page_count=page_count,
        character_count=character_count,
        has_text=character_count > 0,
    )


def extract_pdf_text_bounded(path: Path, limit: int) -> tuple[str, bool]:
    """Return bounded text plus an explicit partial-evidence indicator."""
    result = _run_pdf_text_worker(path, "extract", limit)
    return str(result["text"]), bool(result["truncated"])


def extract_pdf_text(path: Path, limit: int) -> str:
    """Extracts text from a PDF file.

    Args:
        path: Resolved PDF file path.
        limit: Maximum number of characters to return.

    Returns:
        Extracted text capped to ``limit`` characters.
    """
    return extract_pdf_text_bounded(path, limit)[0]


def append_limited(parts: list[str], text: str, total: int, limit: int) -> int:
    """Appends text and returns the updated character count.

    Args:
        parts: Text fragments collected so far.
        text: Text fragment to append.
        total: Current approximate character count.
        limit: Maximum desired character count.

    Returns:
        Updated approximate character count.
    """
    separator = 1 if parts else 0
    remaining = max(0, limit - total - separator)
    if not remaining:
        return min(total, limit)
    bounded = text[:remaining]
    parts.append(bounded)
    return total + separator + len(bounded)


_PAGE_RELATIONS: dict[str, str] = {
    "eq": "eq",
    "==": "eq",
    "ne": "ne",
    "!=": "ne",
    "lt": "lt",
    "<": "lt",
    "le": "le",
    "<=": "le",
    "gt": "gt",
    ">": "gt",
    "ge": "ge",
    ">=": "ge",
}


class PdfCheckPagesInput(StrictModel):
    """Input for ``pdf.check_pages``.

    Attributes:
        path: Workspace-relative PDF path.
        relation: Comparison operator applied as ``page_count <relation>
            ref_value``. Accepts operator words (``eq``, ``le``) or symbols
            (``==``, ``<=``).
        ref_value: The page count to compare against.
    """

    path: str
    relation: Literal["eq", "==", "ne", "!=", "lt", "<", "le", "<=", "gt", ">", "ge", ">="]
    ref_value: int = Field(ge=0)

    @field_validator("path")
    @classmethod
    def require_pdf_extension(cls, value: str) -> str:
        """Requires the path to target a PDF file.

        Args:
            value: Workspace-relative path from verifier.json.

        Returns:
            The unchanged path when it has a PDF extension.

        Raises:
            ValueError: If the path does not end in ``.pdf``.
        """
        if Path(value).suffix.lower() != ".pdf":
            raise ValueError("pdf.check_pages requires a .pdf file")
        return value


class PdfCheckPagesOutput(StrictModel):
    """Result of comparing a PDF page count to a reference.

    Attributes:
        page_count: Pages in the document.
        match: Whether the page count satisfies the relation. Boolean rather
            than a score because a page-count constraint is inherently binary.
    """

    page_count: int
    match: bool


class CheckPages(SourceCommand[PdfCheckPagesInput, PdfCheckPagesOutput]):
    """Check a PDF's page count against a reference value and relation."""

    name = "check_pages"
    input_model = PdfCheckPagesInput
    output_model = PdfCheckPagesOutput

    def run(
        self, source_input: PdfCheckPagesInput, context: SourceContext
    ) -> PdfCheckPagesOutput:
        """Runs the PDF page-count check.

        Args:
            source_input: Validated page-count input.
            context: Source runtime context.

        Returns:
            The page count and whether it satisfies the relation.
        """
        resolved = context.resolve_path(source_input.path)
        page_count = int(_run_pdf_text_worker(resolved, "pages", 0)["page_count"])
        relation = getattr(operator, _PAGE_RELATIONS[source_input.relation])
        return PdfCheckPagesOutput(
            page_count=page_count,
            match=bool(relation(page_count, source_input.ref_value)),
        )


class PdfExtractAnswersInput(StrictModel):
    """Input for ``pdf.extract_answers``.

    Attributes:
        path: Workspace-relative PDF path.
    """

    path: str

    @field_validator("path")
    @classmethod
    def require_pdf_extension(cls, value: str) -> str:
        """Requires the path to target a PDF file.

        Args:
            value: Workspace-relative path from verifier.json.

        Returns:
            The unchanged path when it has a PDF extension.

        Raises:
            ValueError: If the path does not end in ``.pdf``.
        """
        if Path(value).suffix.lower() != ".pdf":
            raise ValueError("pdf.extract_answers requires a .pdf file")
        return value


class PdfExtractAnswersOutput(StrictModel):
    """Right-hand-side values parsed from ``key = value`` lines.

    Attributes:
        answers: Bounded text after ``=`` on qualifying lines, in page/line
            order. Lets a verifier assert on computed answers without depending
            on their surrounding prose.
        truncated: Whether the aggregate source-content limit cut the evidence.
    """

    answers: list[str]
    truncated: bool


class ExtractAnswers(SourceCommand[PdfExtractAnswersInput, PdfExtractAnswersOutput]):
    """Extract ``key = value`` right-hand sides from a PDF's text."""

    name = "extract_answers"
    input_model = PdfExtractAnswersInput
    output_model = PdfExtractAnswersOutput

    def run(
        self, source_input: PdfExtractAnswersInput, context: SourceContext
    ) -> PdfExtractAnswersOutput:
        """Runs PDF answer extraction.

        Args:
            source_input: Validated extraction input.
            context: Source runtime context.

        Returns:
            The extracted right-hand-side values.
        """
        resolved = context.resolve_path(source_input.path)
        answers, truncated = extract_answers_from_pdf(
            resolved, limit=context.max_content_chars
        )
        return PdfExtractAnswersOutput(answers=answers, truncated=truncated)


def extract_answers_from_pdf(
    path: Path, *, limit: int = 90_000
) -> tuple[list[str], bool]:
    """Parses ``key = value`` right-hand sides from a PDF's text.

    Args:
        path: Resolved PDF file path.
        limit: Maximum aggregate answer characters to return.

    Returns:
        Bounded values in page/line order and whether evidence was truncated.

    Raises:
        SourceDataError: If the PDF is malformed or cannot be opened.
    """
    result = _run_pdf_text_worker(path, "answers", limit)
    answers = result.get("answers")
    if not isinstance(answers, list) or not all(
        isinstance(answer, str) for answer in answers
    ):
        raise SourceDataError("PDF answer extraction returned malformed evidence")
    return answers, bool(result.get("truncated"))


class PdfFindLabeledValueInput(StrictModel):
    """Input for ``pdf.find_labeled_value``.

    Attributes:
        path: Workspace-relative PDF path.
        label: Case-insensitive label stem (``"Substantive"`` matches
            ``Substantive changes: 8`` and ``SUBSTANTIVE: 8``). Matched inside
            one text block so a neighbouring column never supplies the value.
    """

    path: str
    label: str = Field(min_length=2, max_length=80)

    @field_validator("path")
    @classmethod
    def require_pdf_extension(cls, value: str) -> str:
        """Requires the path to target a PDF file."""
        if Path(value).suffix.lower() != ".pdf":
            raise ValueError("pdf.find_labeled_value requires a .pdf file")
        return value

    @field_validator("label")
    @classmethod
    def require_word_label(cls, value: str) -> str:
        """Requires a plain word stem so the label cannot smuggle a regex."""
        if not value.strip() or not all(ch.isalnum() or ch in " _-" for ch in value):
            raise ValueError("pdf.find_labeled_value label must be a plain word stem")
        return value.strip()


class PdfFindLabeledValueOutput(StrictModel):
    """The first ``<label …>: <number>`` pair found in reading order.

    Numbers are read as people write them (``labeled_value``): ``$1,200``,
    ``USD 55``, ``55 (USD)``, ``12%``, ``(1,200)`` = -1200, ``1.2 million``;
    the label may carry a bracketed unit (``Total rebate (USD): 55``).

    Attributes:
        found: Whether any block carries the label followed by a number.
        label: The label text as written in the document (None if not found).
        value: The number bound to the label (None if not found).
        value_text: The number exactly as written (``$1,200``).
        unit: Currency or ``%`` written with the number or in the label's
            brackets, else None.
        alternatives: Numbers hedged onto the same line after the value
            (``8 or 9``, ``7 (possibly 5)``); empty when the figure is stated once.
        page: 1-based page of the first hit.
        block: Text-block index of the first hit on that page.
        line: The line carrying the pair, for the failure reason.
        occurrences: How many label/number pairs matched in the document.
        consistent: Whether every occurrence carries the same number.
        all_values: Sorted distinct values across occurrences.
    """

    found: bool
    label: str | None
    value: float | None
    value_text: str | None = None
    unit: str | None = None
    alternatives: list[float]
    page: int | None
    block: int | None
    line: str | None
    occurrences: int
    consistent: bool
    all_values: list[float]


def find_pdf_labeled_value(path: Path, label: str) -> dict[str, Any]:
    """Match ``label`` against each text block (a label alone at the end of a
    block may take its number from the start of the next block)."""
    from . import labeled_value as lv

    raw = _run_pdf_text_worker(path, "blocks", 0).get("blocks")
    if not isinstance(raw, list):
        raise SourceDataError("PDF label lookup returned malformed evidence")
    pattern = lv.label_pattern(label, anchored=False)
    tail = lv.tail_pattern(label)
    hits: list[dict[str, Any]] = []
    for position, (page, block, text) in enumerate(raw):
        text = str(text or "")
        if position + 1 < len(raw) and raw[position + 1][0] == page and tail.search(text):
            following = str(raw[position + 1][2] or "")
            if lv.HEAD_NUMBER_RE.match(following):
                text = text.rstrip() + " " + following
        hits.extend(lv.find_hits(text, pattern, {"page": int(page), "block": int(block)}, 500))
    return lv.summarize(hits, ("page", "block"))


class FindLabeledValue(SourceCommand[PdfFindLabeledValueInput, PdfFindLabeledValueOutput]):
    """Bind a headline figure to its label inside one text block."""

    name = "find_labeled_value"
    input_model = PdfFindLabeledValueInput
    output_model = PdfFindLabeledValueOutput

    def run(
        self, source_input: PdfFindLabeledValueInput, context: SourceContext
    ) -> PdfFindLabeledValueOutput:
        """Runs the label/value lookup."""
        resolved = context.resolve_path(source_input.path)
        result = find_pdf_labeled_value(resolved, source_input.label)
        try:
            return PdfFindLabeledValueOutput.model_validate(result)
        except ValueError as exc:
            raise SourceDataError("PDF label lookup returned malformed evidence") from exc



class PdfPathInput(StrictModel):
    """Input naming one PDF artifact.

    Attributes:
        path: Workspace-relative PDF path.
    """

    path: str

    @field_validator("path")
    @classmethod
    def require_pdf_extension(cls, value: str) -> str:
        """Requires the path to target a PDF file."""
        if Path(value).suffix.lower() != ".pdf":
            raise ValueError("this pdf command requires a .pdf file")
        return value


class PdfInspectMetadataOutput(StrictModel):
    """Document-information metadata, each "" when unset.

    A task that asks "set the PDF's title to X and the author to Y" grades
    ``$.title`` / ``$.author`` with ``equals``; nothing here is checked unless
    a task asks for it.

    Attributes:
        title: ``/Title``.
        author: ``/Author``.
        subject: ``/Subject``.
        keywords: ``/Keywords``.
        creator: ``/Creator`` (the authoring application).
        producer: ``/Producer`` (the PDF library).
        page_count: Pages in the document.
    """

    title: str
    author: str
    subject: str
    keywords: str
    creator: str
    producer: str
    page_count: int


class InspectMetadata(SourceCommand[PdfPathInput, PdfInspectMetadataOutput]):
    """Read a PDF's title, author, subject, keywords, creator and producer."""

    name = "inspect_metadata"
    input_model = PdfPathInput
    output_model = PdfInspectMetadataOutput

    def run(self, source_input: PdfPathInput, context: SourceContext) -> PdfInspectMetadataOutput:
        resolved = context.resolve_path(source_input.path)
        result = _run_pdf_text_worker(resolved, "meta", 500)
        try:
            return PdfInspectMetadataOutput.model_validate(result)
        except ValueError as exc:
            raise SourceDataError("PDF metadata returned malformed evidence") from exc


# PDF base-14 families: never embedded by convention, so "system default font"
# in a client rule means one of these.
_BASE14_FAMILIES = {"helvetica", "times", "courier", "symbol", "zapfdingbats"}


def _font_family(name: str) -> str:
    """Family part of a PostScript font name: ``Inter-Bold`` -> ``Inter``,
    ``Arial,BoldItalic`` -> ``Arial``, ``TimesNewRomanPS-BoldMT`` ->
    ``TimesNewRomanPS``. Approximate by nature; exact names stay in ``fonts``."""
    family = re.split(r"[-,]", name, maxsplit=1)[0].strip()
    return family or name


class PdfFont(StrictModel):
    """One font that draws text in the document (from text spans, matched to
    the page's font resources for the embedded flag).

    Attributes:
        name: PostScript base-font name without a subset prefix (``ABCDEF+``).
        family: ``name`` up to the first ``-`` or ``,`` (style suffix dropped).
        type: Font type (``TrueType``, ``Type1``, ``Type0``, ``Type3``...).
        embedded: Whether the font program is embedded in the file.
        subset: Whether the stored name carried a subset prefix.
        standard14: Whether the family is a PDF base-14 font (Helvetica, Times,
            Courier, Symbol, ZapfDingbats).
        pages: 1-based pages that use it (first 50).
    """

    name: str
    family: str
    type: str
    embedded: bool
    subset: bool
    standard14: bool
    pages: list[int]


class PdfInspectFontsOutput(StrictModel):
    """Fonts used by the PDF, with the embedded flag.

    Attributes:
        fonts: One entry per distinct (name, type, embedded) font resource.
        font_names: Distinct ``name`` values, sorted.
        distinct_font_count: ``len(font_names)``.
        families: Distinct ``family`` values, sorted.
        family_count: ``len(families)``.
        all_embedded: Whether every font is embedded (True for a PDF with no
            fonts, e.g. an image-only scan; pair with ``inspect_document``).
        non_embedded_names: Names of fonts that are not embedded, sorted.
        standard14_count: Font entries whose family is a base-14 font.
        unused_font_names: Font resources no text span draws with (left out
            of every field above; a generator may register one it never uses).
    """

    fonts: list[PdfFont]
    font_names: list[str]
    distinct_font_count: int
    families: list[str]
    family_count: int
    all_embedded: bool
    non_embedded_names: list[str]
    standard14_count: int
    unused_font_names: list[str] = Field(default_factory=list)


class InspectFonts(SourceCommand[PdfPathInput, PdfInspectFontsOutput]):
    """List a PDF's fonts with their embedded flag."""

    name = "inspect_fonts"
    input_model = PdfPathInput
    output_model = PdfInspectFontsOutput

    def run(self, source_input: PdfPathInput, context: SourceContext) -> PdfInspectFontsOutput:
        resolved = context.resolve_path(source_input.path)
        result = _run_pdf_text_worker(resolved, "fonts", 500)
        fonts: list[PdfFont] = []
        for entry in result.get("fonts") or []:
            name = str(entry.get("name") or "")
            family = _font_family(name)
            fonts.append(PdfFont(
                name=name,
                family=family,
                type=str(entry.get("type") or ""),
                embedded=bool(entry.get("embedded")),
                subset=bool(entry.get("subset")),
                standard14=re.sub(r"[^a-z0-9]", "", family.lower()) in _BASE14_FAMILIES,
                pages=[int(page) for page in entry.get("pages") or []],
            ))
        names = sorted({font.name for font in fonts})
        families = sorted({font.family for font in fonts})
        return PdfInspectFontsOutput(
            fonts=fonts,
            font_names=names,
            distinct_font_count=len(names),
            families=families,
            family_count=len(families),
            all_embedded=all(font.embedded for font in fonts),
            non_embedded_names=sorted({font.name for font in fonts if not font.embedded}),
            standard14_count=sum(1 for font in fonts if font.standard14),
            unused_font_names=[str(name) for name in result.get("unused") or []],
        )


class PdfLink(StrictModel):
    """A URI link annotation.

    Attributes:
        page: 1-based page.
        uri: Link target.
    """

    page: int
    uri: str


class PdfUrlText(StrictModel):
    """A URL written in the page text.

    Attributes:
        page: 1-based page.
        text: The URL-looking word (``http://``, ``https://`` or ``www.``),
            surrounding punctuation stripped.
        linked: Whether a URI link annotation covers the word's box.
    """

    page: int
    text: str
    linked: bool


class PdfInspectLinksOutput(StrictModel):
    """Clickable links and URL-looking text in the PDF.

    Attributes:
        links: URI link annotations (first 500).
        link_count: All URI link annotations.
        uris: Distinct link targets, sorted.
        url_texts: URL-looking words in the text (first 500), each with
            whether a link covers it.
        url_text_count: ``len(url_texts)``.
        unlinked_url_count: URL-looking words no link covers; ``equals 0``
            means "every URL written in the document is clickable".
        unlinked_urls: Those words' text.
    """

    links: list[PdfLink]
    link_count: int
    uris: list[str]
    url_texts: list[PdfUrlText]
    url_text_count: int
    unlinked_url_count: int
    unlinked_urls: list[str]


class InspectLinks(SourceCommand[PdfPathInput, PdfInspectLinksOutput]):
    """List URI links and URL text that has no link."""

    name = "inspect_links"
    input_model = PdfPathInput
    output_model = PdfInspectLinksOutput

    def run(self, source_input: PdfPathInput, context: SourceContext) -> PdfInspectLinksOutput:
        resolved = context.resolve_path(source_input.path)
        result = _run_pdf_text_worker(resolved, "links", 500)
        links = [PdfLink.model_validate(item) for item in result.get("links") or []]
        url_texts = [PdfUrlText.model_validate(item) for item in result.get("url_texts") or []]
        unlinked = [item.text for item in url_texts if not item.linked]
        return PdfInspectLinksOutput(
            links=links,
            link_count=int(result.get("link_count") or 0),
            uris=sorted({link.uri for link in links}),
            url_texts=url_texts,
            url_text_count=len(url_texts),
            unlinked_url_count=len(unlinked),
            unlinked_urls=unlinked,
        )


class PdfCodepointSample(StrictModel):
    """One occurrence of a Unicode super/subscript character.

    Attributes:
        page: 1-based page.
        char: The character.
        codepoint: ``U+XXXX``.
        context: Up to 20 characters either side.
    """

    page: int
    char: str
    codepoint: str
    context: str


class PdfScanCodepointsOutput(StrictModel):
    """Unicode superscript/subscript characters in the text layer.

    Covers U+2070-U+209F (superscripts and subscripts block) plus U+00B2,
    U+00B3, U+00B9 (Latin-1 superscript two, three, one). A real superscript
    footnote drawn with a smaller raised font is ordinary digits and does not
    count.

    Attributes:
        count: Occurrences across the document; ``equals 0`` means none.
        counts: Occurrences per character.
        samples: First 20 occurrences with context.
    """

    count: int
    counts: dict[str, int]
    samples: list[PdfCodepointSample]


class ScanCodepoints(SourceCommand[PdfPathInput, PdfScanCodepointsOutput]):
    """Count Unicode superscript/subscript code points in a PDF's text."""

    name = "scan_codepoints"
    input_model = PdfPathInput
    output_model = PdfScanCodepointsOutput

    def run(self, source_input: PdfPathInput, context: SourceContext) -> PdfScanCodepointsOutput:
        resolved = context.resolve_path(source_input.path)
        result = _run_pdf_text_worker(resolved, "codepoints", 500)
        counts = {str(k): int(v) for k, v in (result.get("counts") or {}).items()}
        return PdfScanCodepointsOutput(
            count=sum(counts.values()),
            counts=counts,
            samples=[PdfCodepointSample.model_validate(item) for item in result.get("samples") or []],
        )


class PdfTableSummary(StrictModel):
    """One table PyMuPDF's ``find_tables`` detected.

    Attributes:
        page: 1-based page.
        header: First row's cells, whitespace collapsed.
        row_count: Rows including the header row.
        column_count: Cells in the widest row.
    """

    page: int
    header: list[str]
    row_count: int
    column_count: int


class PdfInspectTablesOutput(StrictModel):
    """Tables detected in the PDF.

    Detection uses ``page.find_tables()`` with its default ``lines`` strategy:
    a table drawn with ruling lines (cell borders or row rules) is found; a
    borderless grid laid out with whitespace only is NOT, by design, because
    the whitespace strategy also "finds" tables in ordinary prose columns.
    Use this only when the task asks for a ruled table.

    Attributes:
        table_count: Tables detected across all pages.
        tables: Per-table summary in page order.
    """

    table_count: int
    tables: list[PdfTableSummary]


def _clean_cell(value: Any) -> str:
    return " ".join(str(value or "").split())


def _pdf_tables(path: Path) -> list[dict[str, Any]]:
    result = _run_pdf_text_worker(path, "tables", 500)
    tables = result.get("tables")
    if not isinstance(tables, list):
        raise SourceDataError("PDF table detection returned malformed evidence")
    return [
        {"page": int(table.get("page") or 0),
         "rows": [[_clean_cell(cell) for cell in row] for row in table.get("rows") or []]}
        for table in tables
    ]


class InspectTables(SourceCommand[PdfPathInput, PdfInspectTablesOutput]):
    """Count and summarize ruled tables in a PDF."""

    name = "inspect_tables"
    input_model = PdfPathInput
    output_model = PdfInspectTablesOutput

    def run(self, source_input: PdfPathInput, context: SourceContext) -> PdfInspectTablesOutput:
        resolved = context.resolve_path(source_input.path)
        tables = _pdf_tables(resolved)
        return PdfInspectTablesOutput(
            table_count=len(tables),
            tables=[
                PdfTableSummary(
                    page=table["page"],
                    header=table["rows"][0] if table["rows"] else [],
                    row_count=len(table["rows"]),
                    column_count=max((len(row) for row in table["rows"]), default=0),
                )
                for table in tables
            ],
        )


class PdfReadTableInput(StrictModel):
    """Input for ``pdf.read_table``.

    Attributes:
        path: Workspace-relative PDF path.
        table_index: Zero-based index into detected tables in page order;
            ``None`` searches every table (first match wins).
        header_match: Optional regex tried against each row rendered as
            ``cell|cell|...``; the first matching row is the header. Without
            it the first row of the selected table is the header.
    """

    path: str
    table_index: int | None = Field(default=None, ge=0)
    header_match: str | None = None

    @field_validator("path")
    @classmethod
    def require_pdf_extension(cls, value: str) -> str:
        """Requires the path to target a PDF file."""
        if Path(value).suffix.lower() != ".pdf":
            raise ValueError("pdf.read_table requires a .pdf file")
        return value

    @field_validator("header_match")
    @classmethod
    def require_valid_regex(cls, value: str | None) -> str | None:
        """The header pattern must compile."""
        if value is not None:
            try:
                re.compile(value)
            except re.error as exc:
                raise ValueError(f"header_match is not a valid regex: {exc}") from exc
        return value


class PdfReadTableOutput(RootModel[list[dict[str, str]]]):
    """One header-keyed mapping per data row, like ``docx.read_table``, so
    ``table_equals`` grades it. Cell text is whitespace-collapsed (a cell
    wrapped onto two lines reads as one line)."""


def header_keyed_rows(
    tables: list[list[list[str]]], table_index: int | None, header_match: str | None, name: str
) -> list[dict[str, str]]:
    """Pick a table and key its data rows by the header row's cells."""
    if not tables:
        raise SourceDataError(f"no table found: {name}")
    if table_index is not None:
        if table_index >= len(tables):
            raise SourceDataError(f"{name} has {len(tables)} table(s), no table_index {table_index}")
        tables = [tables[table_index]]
    chosen: list[list[str]] | None = None
    header_row = 0
    if header_match:
        pattern = re.compile(header_match)
        for table in tables:
            for index, row in enumerate(table):
                if pattern.search("|".join(row)):
                    chosen, header_row = table, index
                    break
            if chosen is not None:
                break
        if chosen is None:
            raise SourceDataError(f"no table row matches header_match {header_match!r}: {name}")
    else:
        chosen = tables[0]
    if not chosen:
        return []
    keys: list[str] = []
    for position, text in enumerate(chosen[header_row]):
        key = text or f"column_{position + 1}"
        keys.append(key if key not in keys else f"{key} ({position + 1})")
    rows: list[dict[str, str]] = []
    for row in chosen[header_row + 1:]:
        if not any(cell.strip() for cell in row):
            continue
        record = {
            (keys[i] if i < len(keys) else f"column_{i + 1}"): cell for i, cell in enumerate(row)
        }
        for key in keys[len(row):]:
            record[key] = ""
        rows.append(record)
    return rows


class ReadTable(SourceCommand[PdfReadTableInput, PdfReadTableOutput]):
    """Read one ruled PDF table as header-keyed rows."""

    name = "read_table"
    input_model = PdfReadTableInput
    output_model = PdfReadTableOutput

    def run(self, source_input: PdfReadTableInput, context: SourceContext) -> PdfReadTableOutput:
        resolved = context.resolve_path(source_input.path)
        tables = [table["rows"] for table in _pdf_tables(resolved)]
        return PdfReadTableOutput(
            header_keyed_rows(tables, source_input.table_index, source_input.header_match, resolved.name)
        )

COMMANDS = (
    ExtractText(),
    InspectDocument(),
    CheckPages(),
    ExtractAnswers(),
    FindLabeledValue(),
    InspectMetadata(),
    InspectFonts(),
    InspectLinks(),
    ScanCodepoints(),
    InspectTables(),
    ReadTable(),
)
