from pathlib import Path

from pydantic import field_validator

from ..models import StrictModel
from ..source_types import SourceCommand, SourceContext


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
    """

    text: str


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
        return PdfExtractTextOutput(text=extract_pdf_text(resolved, context.max_content_chars))


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
    from pypdf import PdfReader

    reader = PdfReader(path)
    character_count = sum(
        len((page.extract_text() or "").strip()) for page in reader.pages
    )
    return PdfInspectDocumentOutput(
        page_count=len(reader.pages),
        character_count=character_count,
        has_text=character_count > 0,
    )


def extract_pdf_text(path: Path, limit: int) -> str:
    """Extracts text from a PDF file.

    Args:
        path: Resolved PDF file path.
        limit: Maximum number of characters to return.

    Returns:
        Extracted text capped to ``limit`` characters.
    """
    from pypdf import PdfReader

    reader = PdfReader(path)
    parts: list[str] = []
    total = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        if not text.strip():
            continue
        total = append_limited(parts, text.strip(), total, limit)
        if total >= limit:
            break
    return "\n".join(parts)[:limit]


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
    parts.append(text)
    return total + len(text) + 1


COMMANDS = (ExtractText(), InspectDocument())
