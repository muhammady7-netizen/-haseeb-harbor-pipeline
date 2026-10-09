import re
from pathlib import Path
from typing import Any

from pydantic import Field, RootModel, field_validator

from ..models import StrictModel
from ..source_types import SourceCapabilityError, SourceCommand, SourceContext, SourceDataError


class MdExtractTextInput(StrictModel):
    """Input for md.extract_text.

    Attributes:
        path: Workspace-relative Markdown path.
    """

    path: str

    @field_validator("path")
    @classmethod
    def require_markdown_extension(cls, value: str) -> str:
        """Requires the path to target a Markdown file.

        Args:
            value: Workspace-relative path from verifier.json.

        Returns:
            The unchanged path when it has a Markdown extension.

        Raises:
            ValueError: If the path does not end in ``.md``.
        """
        if Path(value).suffix.lower() != ".md":
            raise ValueError("md.extract_text requires a .md file")
        return value


class MdExtractTextOutput(StrictModel):
    """Output from md.extract_text.

    Attributes:
        text: Raw UTF-8 Markdown text.
        truncated: Whether the file was longer than the source content limit
            and the text above is only its leading portion. A negative
            assertion cannot be satisfied by content that was cut, so the
            runner needs to know a read was partial.
    """

    text: str
    truncated: bool = False


class ExtractText(SourceCommand[MdExtractTextInput, MdExtractTextOutput]):
    """Reads raw UTF-8 Markdown files."""

    name = "extract_text"
    input_model = MdExtractTextInput
    output_model = MdExtractTextOutput

    def run(self, source_input: MdExtractTextInput, context: SourceContext) -> MdExtractTextOutput:
        """Reads Markdown text from a workspace file.

        Args:
            source_input: Validated Markdown extraction input.
            context: Source runtime context.

        Returns:
            Raw Markdown text capped to the configured source content limit.

        """
        resolved = context.resolve_path(source_input.path)
        raw = resolved.read_text(encoding="utf-8-sig")
        limit = context.max_content_chars
        return MdExtractTextOutput(text=raw[:limit], truncated=len(raw) > limit)


COMMANDS = (ExtractText(),)


# --------------------------------------------------------------------------
# Structure: md.inspect_document / md.read_table / md.find_labeled_value
# --------------------------------------------------------------------------
#
# A Markdown deliverable is parsed with markdown-it-py (CommonMark plus GFM
# tables and strikethrough), so a heading is a heading whether written ``## X``
# or underlined, a list is a list whether bulleted with ``-``, ``*`` or ``1.``,
# and emphasis or escaping never changes a cell's text. Code blocks and raw
# HTML (comments included) are not prose and are not read.

MAX_MD_ITEMS = 2_000


class MdPathInput(StrictModel):
    """Input naming one Markdown artifact.

    Attributes:
        path: Workspace-relative Markdown path (``.md``).
    """

    path: str

    @field_validator("path")
    @classmethod
    def require_markdown_extension(cls, value: str) -> str:
        """Requires the path to target a Markdown file."""
        if Path(value).suffix.lower() not in {".md", ".markdown"}:
            raise ValueError("this md command requires a .md file")
        return value


def _markdown_tokens(text: str) -> list[Any]:
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:  # pragma: no cover - present in the v7 image
        raise SourceCapabilityError("md structure commands require markdown-it-py") from exc
    parser = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])
    return parser.parse(text)


def _inline_text(token: Any, *, breaks: str = " ") -> str:
    """Reader-visible text of an inline token: markup dropped, code kept."""
    parts: list[str] = []
    for child in token.children or []:
        if child.type in {"text", "code_inline"}:
            parts.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            parts.append(breaks)
        elif child.type == "image":
            parts.append(child.content or "")
    text = "".join(parts)
    return text if breaks == "\n" else " ".join(text.split())


def _inline_links(token: Any) -> list[str]:
    """Link targets inside an inline token, in order (``[t](href)`` and ``<href>``)."""
    return [
        str(child.attrs.get("href", ""))
        for child in token.children or []
        if child.type == "link_open" and child.attrs.get("href")
    ]


def _read_markdown(path: Path, limit: int, *, strict: bool) -> tuple[str, bool]:
    raw = path.read_text(encoding="utf-8-sig")
    truncated = len(raw) > limit
    if truncated and strict:
        raise SourceDataError("Markdown document exceeds the source content limit")
    return raw[:limit], truncated


class MdHeading(StrictModel):
    """One heading.

    Attributes:
        level: 1-6.
        text: Heading text, markup dropped.
        line: 1-based source line.
    """

    level: int
    text: str
    line: int


class MdList(StrictModel):
    """One list (a nested list is its own entry with a greater depth).

    Attributes:
        ordered: Numbered list.
        depth: 0 for a top-level list, 1 inside a list item, ...
        line: 1-based source line.
        heading: Nearest preceding heading text ("" before any heading).
        items: Item texts, markup dropped (a nested list's items are not
            folded into its parent item).
    """

    ordered: bool
    depth: int
    line: int
    heading: str
    items: list[str]


class MdTable(StrictModel):
    """One GFM table.

    Attributes:
        line: 1-based source line.
        heading: Nearest preceding heading text ("" before any heading).
        header: Header cells.
        rows: Data rows keyed by header cell (``docx.read_table`` shape).
        links: Per data row (parallel to ``rows``), the link targets of each
            cell that has any: ``{column: [href, ...]}``.
    """

    line: int
    heading: str
    header: list[str]
    rows: list[dict[str, str]]
    links: list[dict[str, list[str]]] = Field(default_factory=list)


class MdLink(StrictModel):
    """One link.

    Attributes:
        text: Link text.
        href: Target.
    """

    text: str
    href: str


class MdInspectDocumentOutput(StrictModel):
    """Markdown structure.

    Attributes:
        headings: Every heading in order (first 2000).
        heading_texts: ``headings[*].text``.
        heading_count: All headings.
        lists: Every list in order (first 2000).
        list_count: All lists.
        list_item_count: Items across all lists.
        tables: Every table in order (first 2000).
        table_count: All tables.
        links: Every link in order (first 2000).
        link_count: All links.
        paragraph_count: Paragraphs outside lists, tables and quotes.
        truncated: The file was longer than the source content limit and only
            its leading part was parsed.
    """

    headings: list[MdHeading]
    heading_texts: list[str]
    heading_count: int
    lists: list[MdList]
    list_count: int
    list_item_count: int
    tables: list[MdTable]
    table_count: int
    links: list[MdLink]
    link_count: int
    paragraph_count: int
    truncated: bool


def _keyed_rows(header: list[str], body: list[list[str]]) -> list[dict[str, str]]:
    keys: list[str] = []
    for position, cell in enumerate(header):
        key = cell or f"column_{position + 1}"
        keys.append(key if key not in keys else f"{key} ({position + 1})")
    rows: list[dict[str, str]] = []
    for row in body:
        if not any(cell.strip() for cell in row):
            continue
        record = {(keys[i] if i < len(keys) else f"column_{i + 1}"): cell for i, cell in enumerate(row)}
        for key in keys[len(row):]:
            record[key] = ""
        rows.append(record)
    return rows


def markdown_structure(text: str) -> dict[str, Any]:
    """Headings, lists, tables, links and paragraph count of ``text``."""
    tokens = _markdown_tokens(text)
    headings: list[dict[str, Any]] = []
    lists: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    links: list[dict[str, str]] = []
    paragraphs = 0
    list_stack: list[dict[str, Any]] = []
    item_depth = 0
    quote_depth = 0
    current_heading = ""
    index = 0
    while index < len(tokens):
        token = tokens[index]
        kind = token.type
        line = (token.map[0] + 1) if token.map else 0
        if kind == "heading_open":
            inline = tokens[index + 1]
            current_heading = _inline_text(inline)
            headings.append({"level": int(token.tag[1]), "text": current_heading, "line": line})
        elif kind in {"bullet_list_open", "ordered_list_open"}:
            entry = {"ordered": kind == "ordered_list_open", "depth": len(list_stack),
                     "line": line, "heading": current_heading, "items": []}
            lists.append(entry)
            list_stack.append(entry)
        elif kind in {"bullet_list_close", "ordered_list_close"}:
            if list_stack:
                list_stack.pop()
        elif kind == "list_item_open":
            item_depth += 1
            if list_stack:
                list_stack[-1]["items"].append("")
        elif kind == "list_item_close":
            item_depth = max(0, item_depth - 1)
        elif kind == "blockquote_open":
            quote_depth += 1
        elif kind == "blockquote_close":
            quote_depth = max(0, quote_depth - 1)
        elif kind == "paragraph_open":
            if not item_depth and not quote_depth:
                paragraphs += 1
            if list_stack and item_depth and tokens[index + 1].type == "inline":
                items = list_stack[-1]["items"]
                piece = _inline_text(tokens[index + 1])
                items[-1] = (items[-1] + " " + piece).strip() if items else piece
        elif kind == "table_open":
            header: list[str] = []
            body: list[list[str]] = []
            body_links: list[list[list[str]]] = []
            row: list[str] | None = None
            row_links: list[list[str]] = []
            in_head = False
            index += 1
            while index < len(tokens) and tokens[index].type != "table_close":
                inner = tokens[index]
                if inner.type == "thead_open":
                    in_head = True
                elif inner.type == "thead_close":
                    in_head = False
                elif inner.type == "tr_open":
                    row, row_links = [], []
                elif inner.type == "tr_close" and row is not None:
                    if in_head:
                        header = row
                    else:
                        body.append(row)
                        body_links.append(row_links)
                    row = None
                elif inner.type == "inline" and row is not None:
                    row.append(_inline_text(inner))
                    row_links.append(_inline_links(inner))
                index += 1
            linked_body = [
                [" ".join([cell] + hrefs).strip() for cell, hrefs in zip(cells, links)] + cells[len(links):]
                for cells, links in zip(body, body_links)
            ]
            keys = list(_keyed_rows(header, [[c or "x" for c in header]])[0]) if header else []
            tables.append({"line": line, "heading": current_heading, "header": header,
                           "rows": _keyed_rows(header, body),
                           "linked_rows": _keyed_rows(header, linked_body),
                           "links": [
                               {(keys[i] if i < len(keys) else f"column_{i + 1}"): hrefs
                                for i, hrefs in enumerate(links) if hrefs}
                               for cells, links in zip(body, body_links) if any(c.strip() for c in cells)
                           ]})
        elif kind == "inline":
            children = token.children or []
            for position, child in enumerate(children):
                if child.type == "link_open":
                    label: list[str] = []
                    for follower in children[position + 1:]:
                        if follower.type == "link_close":
                            break
                        if follower.type in {"text", "code_inline"}:
                            label.append(follower.content)
                    links.append({"text": "".join(label).strip(), "href": str(child.attrs.get("href", ""))})
        index += 1
    return {"headings": headings, "lists": lists, "tables": tables, "links": links, "paragraphs": paragraphs}


class InspectDocument(SourceCommand[MdPathInput, MdInspectDocumentOutput]):
    """Parse Markdown into headings, lists, tables and links."""

    name = "inspect_document"
    input_model = MdPathInput
    output_model = MdInspectDocumentOutput

    def run(self, source_input: MdPathInput, context: SourceContext) -> MdInspectDocumentOutput:
        resolved = context.resolve_path(source_input.path)
        text, truncated = _read_markdown(resolved, context.max_content_chars, strict=False)
        found = markdown_structure(text)
        headings = found["headings"]
        return MdInspectDocumentOutput(
            headings=[MdHeading.model_validate(h) for h in headings[:MAX_MD_ITEMS]],
            heading_texts=[h["text"] for h in headings[:MAX_MD_ITEMS]],
            heading_count=len(headings),
            lists=[MdList.model_validate(entry) for entry in found["lists"][:MAX_MD_ITEMS]],
            list_count=len(found["lists"]),
            list_item_count=sum(len(entry["items"]) for entry in found["lists"]),
            tables=[
                MdTable(line=t["line"], heading=t["heading"], header=t["header"], rows=t["rows"], links=t["links"])
                for t in found["tables"][:MAX_MD_ITEMS]
            ],
            table_count=len(found["tables"]),
            links=[MdLink.model_validate(link) for link in found["links"][:MAX_MD_ITEMS]],
            link_count=len(found["links"]),
            paragraph_count=found["paragraphs"],
            truncated=truncated,
        )


def _normal_heading(text: str) -> str:
    """Compare headings ignoring case, spacing, a trailing colon and a leading
    section number (``2.``, ``2.1``, ``II.``, ``A)``)."""
    cleaned = re.sub(r"^\s*(?:\d+(?:\.\d+)*|[IVXLC]+|[A-Z])[.)]?\s+", "", text.strip())
    return " ".join(cleaned.rstrip(":").split()).casefold()


class MdReadTableInput(StrictModel):
    """Input for ``md.read_table``.

    Attributes:
        path: Workspace-relative Markdown path.
        heading: Optional section heading: the table is looked for between this
            heading and the next heading of the same or a higher level. Matched
            ignoring case, spacing, a trailing colon and a leading section
            number.
        table_index: Zero-based index among the candidate tables (within the
            heading's section when ``heading`` is given). Default 0.
        header_match: Optional regex that the header row rendered as
            ``cell|cell|...`` must match, so a different table cannot stand in.
        link_targets: When True, a cell holding links reads as its text
            followed by each link target (``[open](https://x/abc)`` reads
            ``open https://x/abc``), so an id that lives only in a link can key
            a row (``table_equals`` with ``id_pattern``). Default False: text only.
    """

    path: str
    heading: str | None = Field(default=None, min_length=1, max_length=300)
    table_index: int = Field(default=0, ge=0)
    header_match: str | None = None
    link_targets: bool = False

    @field_validator("path")
    @classmethod
    def require_markdown_extension(cls, value: str) -> str:
        """Requires the path to target a Markdown file."""
        if Path(value).suffix.lower() not in {".md", ".markdown"}:
            raise ValueError("md.read_table requires a .md file")
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


class MdReadTableOutput(RootModel[list[dict[str, str]]]):
    """One header-keyed mapping per data row (``docx.read_table`` shape), so
    ``table_equals`` grades it. Cell text has Markdown emphasis and escapes
    removed."""


def read_markdown_table(
    text: str, heading: str | None, table_index: int, header_match: str | None,
    link_targets: bool = False,
) -> list[dict[str, str]]:
    """Header-keyed rows of the selected table."""
    found = markdown_structure(text)
    candidates = found["tables"]
    if heading is not None:
        wanted = _normal_heading(heading)
        sections: list[tuple[int, int]] = []
        heads = found["headings"]
        for position, head in enumerate(heads):
            if _normal_heading(head["text"]) != wanted:
                continue
            end = next(
                (later["line"] for later in heads[position + 1:] if later["level"] <= head["level"]),
                10**9,
            )
            sections.append((head["line"], end))
        if not sections:
            raise SourceDataError(f"no heading {heading!r} in the Markdown document")
        start, end = sections[0]
        candidates = [table for table in candidates if start < table["line"] < end]
    if table_index >= len(candidates):
        where = f" under {heading!r}" if heading is not None else ""
        raise SourceDataError(f"{len(candidates)} table(s){where}, no table_index {table_index}")
    table = candidates[table_index]
    if header_match and not re.search(header_match, "|".join(table["header"])):
        raise SourceDataError(f"table header {table['header']} does not match {header_match!r}")
    return table["linked_rows"] if link_targets else table["rows"]


class ReadTable(SourceCommand[MdReadTableInput, MdReadTableOutput]):
    """Read one Markdown table, by section heading or index, as keyed rows."""

    name = "read_table"
    input_model = MdReadTableInput
    output_model = MdReadTableOutput

    def run(self, source_input: MdReadTableInput, context: SourceContext) -> MdReadTableOutput:
        resolved = context.resolve_path(source_input.path)
        text, _ = _read_markdown(resolved, context.max_content_chars, strict=True)
        return MdReadTableOutput(read_markdown_table(
            text, source_input.heading, source_input.table_index, source_input.header_match,
            source_input.link_targets,
        ))


class MdFindLabeledValueInput(StrictModel):
    """Input for ``md.find_labeled_value``.

    Attributes:
        path: Workspace-relative Markdown path.
        label: Case-insensitive label stem, as for ``pdf.find_labeled_value``.
    """

    path: str
    label: str = Field(min_length=2, max_length=80)

    @field_validator("path")
    @classmethod
    def require_markdown_extension(cls, value: str) -> str:
        """Requires the path to target a Markdown file."""
        if Path(value).suffix.lower() not in {".md", ".markdown"}:
            raise ValueError("md.find_labeled_value requires a .md file")
        return value

    @field_validator("label")
    @classmethod
    def require_word_label(cls, value: str) -> str:
        """Requires a plain word stem so the label cannot smuggle a regex."""
        if not value.strip() or not all(ch.isalnum() or ch in " _-" for ch in value):
            raise ValueError("md.find_labeled_value label must be a plain word stem")
        return value.strip()


class MdFindLabeledValueOutput(StrictModel):
    """The first line opening with ``<label …>: <number>``, same contract and
    number reading as ``pdf.find_labeled_value``. Lines are read from
    paragraphs, list items, block quotes and headings with Markdown markup
    removed (``**Total rebate:** $55`` reads ``Total rebate: $55``); table
    cells and code blocks are not lines (use ``md.read_table``).

    Attributes:
        found / label / value / value_text / unit / alternatives / line /
        occurrences / consistent / all_values: As ``pdf.find_labeled_value``.
        line_number: 1-based source line of the first hit.
    """

    found: bool
    label: str | None
    value: float | None
    value_text: str | None
    unit: str | None
    alternatives: list[float]
    line: str | None
    line_number: int | None
    occurrences: int
    consistent: bool
    all_values: list[float]


def find_markdown_labeled_value(text: str, label: str) -> dict[str, Any]:
    """Line-anchored label lookup over the prose of ``text``."""
    from . import labeled_value as lv

    pattern = lv.label_pattern(label, anchored=True)
    hits: list[dict[str, Any]] = []
    in_table = 0
    for token in _markdown_tokens(text):
        if token.type == "table_open":
            in_table += 1
        elif token.type == "table_close":
            in_table -= 1
        if token.type != "inline" or in_table or not token.map:
            continue
        prose = _inline_text(token, breaks="\n")
        for hit in lv.find_hits(prose, pattern, {}, 500):
            offset = prose[: prose.find(hit["line"])].count("\n") if hit["line"] in prose else 0
            hit["line_number"] = token.map[0] + 1 + offset
            hits.append(hit)
    return lv.summarize(hits, ("line_number",))


class FindLabeledValue(SourceCommand[MdFindLabeledValueInput, MdFindLabeledValueOutput]):
    """Bind a figure to the label that opens its line."""

    name = "find_labeled_value"
    input_model = MdFindLabeledValueInput
    output_model = MdFindLabeledValueOutput

    def run(self, source_input: MdFindLabeledValueInput, context: SourceContext) -> MdFindLabeledValueOutput:
        resolved = context.resolve_path(source_input.path)
        text, _ = _read_markdown(resolved, context.max_content_chars, strict=True)
        return MdFindLabeledValueOutput.model_validate(find_markdown_labeled_value(text, source_input.label))


COMMANDS = COMMANDS + (InspectDocument(), ReadTable(), FindLabeledValue())
