import csv as stdlib_csv
import io
from pathlib import Path

from pydantic import field_validator

from ..models import StrictModel
from ..source_types import SourceCommand, SourceContext


class CsvExtractTextInput(StrictModel):
    """Input for csv.extract_text.

    Attributes:
        path: Workspace-relative CSV path.
    """

    path: str

    @field_validator("path")
    @classmethod
    def require_csv_extension(cls, value: str) -> str:
        """Requires the path to target a CSV file.

        Args:
            value: Workspace-relative path from verifier.json.

        Returns:
            The unchanged path when it has a CSV extension.

        Raises:
            ValueError: If the path does not end in ``.csv``.
        """
        if Path(value).suffix.lower() != ".csv":
            raise ValueError("csv.extract_text requires a .csv file")
        return value


class CsvExtractTextOutput(StrictModel):
    """Output from csv.extract_text.

    Attributes:
        text: Raw UTF-8 CSV text.
    """

    text: str


class ExtractText(SourceCommand[CsvExtractTextInput, CsvExtractTextOutput]):
    """Reads raw UTF-8 CSV files."""

    name = "extract_text"
    input_model = CsvExtractTextInput
    output_model = CsvExtractTextOutput

    def run(self, source_input: CsvExtractTextInput, context: SourceContext) -> CsvExtractTextOutput:
        """Reads CSV text from a workspace file.

        Args:
            source_input: Validated CSV extraction input.
            context: Source runtime context.

        Returns:
            Raw CSV text capped to the configured source content limit.

        """
        resolved = context.resolve_path(source_input.path)
        return CsvExtractTextOutput(text=resolved.read_text(encoding="utf-8-sig")[: context.max_content_chars])


class CsvInspectTableInput(StrictModel):
    """Input for ``csv.inspect_table``.

    Attributes:
        path: Workspace-relative CSV path.
    """

    path: str

    @field_validator("path")
    @classmethod
    def require_csv_extension(cls, value: str) -> str:
        """Requires the path to target a CSV file.

        Args:
            value: Workspace-relative path from verifier.json.

        Returns:
            The unchanged path when it has a CSV extension.

        Raises:
            ValueError: If the path does not end in ``.csv``.
        """
        if Path(value).suffix.lower() != ".csv":
            raise ValueError("csv.inspect_table requires a .csv file")
        return value


class CsvInspectTableOutput(StrictModel):
    """CSV table shape expressed as counts and header names.

    Attributes:
        header: The first row's field names, capped to the configured source
            content limit.
        column_count: Fields in the header row. Exact even when ``header`` is
            truncated.
        row_count: Data rows, excluding the header, which is the number a
            prompt means by "one row per region".
        total_row_count: Every non-empty row, header included.
        delimiter: The delimiter the file actually uses, sniffed from its
            content, falling back to ``","``.
    """

    header: list[str]
    column_count: int
    row_count: int
    total_row_count: int
    delimiter: str


class InspectTable(SourceCommand[CsvInspectTableInput, CsvInspectTableOutput]):
    """Report a CSV's header, column count, and row count."""

    name = "inspect_table"
    input_model = CsvInspectTableInput
    output_model = CsvInspectTableOutput

    def run(
        self, source_input: CsvInspectTableInput, context: SourceContext
    ) -> CsvInspectTableOutput:
        """Runs CSV shape inspection.

        Args:
            source_input: Validated table inspection input.
            context: Source runtime context.

        Returns:
            CSV shape as counts and header names.
        """
        resolved = context.resolve_path(source_input.path)
        return inspect_csv_table(resolved, context.max_content_chars)


def inspect_csv_table(path: Path, limit: int) -> CsvInspectTableOutput:
    """Reads a CSV's delimiter, header, and row counts.

    Args:
        path: Resolved CSV file path.
        limit: Maximum number of header characters to return.

    Returns:
        CSV shape as counts and header names.
    """
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return CsvInspectTableOutput(
            header=[], column_count=0, row_count=0, total_row_count=0, delimiter=","
        )

    delimiter = sniff_delimiter(text)
    rows = [
        row
        for row in stdlib_csv.reader(io.StringIO(text), delimiter=delimiter)
        if any(field.strip() for field in row)
    ]
    if not rows:
        return CsvInspectTableOutput(
            header=[],
            column_count=0,
            row_count=0,
            total_row_count=0,
            delimiter=delimiter,
        )

    header: list[str] = []
    total = 0
    for field in rows[0]:
        if total >= limit:
            break
        header.append(field)
        total += len(field) + 1
    return CsvInspectTableOutput(
        header=header,
        column_count=len(rows[0]),
        row_count=len(rows) - 1,
        total_row_count=len(rows),
        delimiter=delimiter,
    )


def sniff_delimiter(sample: str) -> str:
    """Detects a CSV delimiter, falling back to a comma.

    ``Sniffer`` raises on input it cannot decide, most commonly a single-column
    file that contains no delimiter at all. Reporting a comma there still gives
    a usable one-column shape instead of failing the whole check.

    Args:
        sample: CSV text to inspect.

    Returns:
        The detected delimiter, or ``","``.
    """
    try:
        return stdlib_csv.Sniffer().sniff(sample[:8192], delimiters=",;\t|").delimiter
    except stdlib_csv.Error:
        return ","


COMMANDS = (ExtractText(), InspectTable())
