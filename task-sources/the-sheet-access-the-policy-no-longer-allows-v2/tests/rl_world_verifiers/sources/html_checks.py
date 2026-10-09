"""HTML well-formedness, banned-CSS and table readers (registered in ``html.COMMANDS``).

``html.validate`` answers the client's "tags closed, syntax correct" with
counts, never a judgment. It runs two independent readers: a tag-stack checker
built on the standard-library tokenizer that knows HTML's void elements and the
end tags HTML lets an author omit (``</p>``, ``</li>``, ``</td>``...), so a valid
page that omits them is not flagged; and libxml2's own HTML parser error log,
reported separately. ``html.inspect_css`` lists declarations a task may forbid
(a ``border-left`` accent bar, gradients). ``html.read_table`` reads a table
picked by CSS selector as header-keyed rows for ``table_equals``.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from pydantic import Field, RootModel, field_validator

from ..models import StrictModel
from ..source_types import (
    SourceAuthoringError,
    SourceCapabilityError,
    SourceCommand,
    SourceContext,
    SourceDataError,
)

MAX_REPORTED = 200

_VOID = frozenset(
    "area base br col embed hr img input link meta source track wbr param keygen "
    "basefont bgsound frame".split()
)
# Elements whose end tag HTML lets an author omit; closing them implicitly is
# not an error.
_OPTIONAL_END = frozenset(
    "html head body p li dt dd rt rp optgroup option colgroup caption thead tbody "
    "tfoot tr td th".split()
)
# A start tag of one of these closes an open <p>.
_CLOSES_P = frozenset(
    "address article aside blockquote details dialog div dl fieldset figcaption "
    "figure footer form h1 h2 h3 h4 h5 h6 header hgroup hr main menu nav ol p pre "
    "search section table ul".split()
)
_HEADINGS = frozenset("h1 h2 h3 h4 h5 h6".split())
_FOREIGN = frozenset({"svg", "math"})
# Start tag -> open elements it closes implicitly, and the elements that bound
# the search (a nested list/table is its own scope).
_IMPLIED = {
    "li": ({"li"}, {"ul", "ol", "menu"}),
    "dt": ({"dt", "dd"}, {"dl"}),
    "dd": ({"dt", "dd"}, {"dl"}),
    "tr": ({"tr", "td", "th"}, {"table", "thead", "tbody", "tfoot"}),
    "td": ({"td", "th"}, {"tr", "table"}),
    "th": ({"td", "th"}, {"tr", "table"}),
    "thead": ({"thead", "tbody", "tfoot", "tr", "td", "th", "caption", "colgroup"}, {"table"}),
    "tbody": ({"thead", "tbody", "tfoot", "tr", "td", "th", "caption", "colgroup"}, {"table"}),
    "tfoot": ({"thead", "tbody", "tfoot", "tr", "td", "th", "caption", "colgroup"}, {"table"}),
    "option": ({"option"}, {"select", "datalist", "optgroup"}),
    "optgroup": ({"option", "optgroup"}, {"select"}),
    "rt": ({"rt", "rp"}, {"ruby"}),
    "rp": ({"rt", "rp"}, {"ruby"}),
}


class _TagStackChecker(HTMLParser):
    """Count unclosed, stray, misnested and malformed tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.counts = {
            "unclosed": 0,
            "stray_end_tag": 0,
            "misnested": 0,
            "duplicate_attribute": 0,
            "self_closed_non_void": 0,
        }
        self.errors: list[dict[str, Any]] = []
        self.ids: dict[str, int] = {}
        self.has_doctype = False
        self.force_closed: list[tuple[str, int]] = []

    def _error(self, kind: str, tag: str) -> int:
        """Count a problem; return its index in ``errors`` (-1 past the cap)."""
        self.counts[kind] += 1
        if len(self.errors) >= MAX_REPORTED:
            return -1
        self.errors.append({"line": self.getpos()[0], "kind": kind, "tag": tag})
        return len(self.errors) - 1

    def _in_foreign(self) -> bool:
        return any(tag in _FOREIGN for tag in self.stack)

    def _pop_to(self, index: int, closing: str) -> None:
        """Pop everything above ``index``; a non-optional element closed this
        way was left open by the author."""
        for tag in self.stack[index + 1:]:
            if tag not in _OPTIONAL_END:
                self._error("unclosed", tag)
        del self.stack[index:]

    def _find(self, names: set[str], bounds: set[str]) -> int:
        for index in range(len(self.stack) - 1, -1, -1):
            tag = self.stack[index]
            if tag in names:
                return index
            if tag in bounds:
                return -1
        return -1

    def handle_decl(self, decl: str) -> None:
        if decl.lower().startswith("doctype"):
            self.has_doctype = True

    def _attributes(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        seen: set[str] = set()
        for name, value in attrs:
            if name in seen:
                self._error("duplicate_attribute", f"{tag}[{name}]")
            seen.add(name)
            if name == "id" and value is not None and value.strip():
                self.ids[value.strip()] = self.ids.get(value.strip(), 0) + 1

    def _open(self, tag: str) -> None:
        if self._in_foreign():
            self.stack.append(tag)
            return
        if tag in {"html", "head", "body"} and tag in self.stack:
            return
        if tag in _CLOSES_P:
            index = self._find({"p"}, {"button", "table", "td", "th"} | _FOREIGN)
            if index >= 0:
                self._pop_to(index, tag)
        if tag in _HEADINGS and self.stack and self.stack[-1] in _HEADINGS:
            self._error("unclosed", self.stack.pop())
        if tag == "a":
            index = self._find({"a"}, set())
            if index >= 0:
                self._error("unclosed", "a")
                del self.stack[index:]
        implied = _IMPLIED.get(tag)
        if implied:
            index = self._find(implied[0], implied[1])
            if index >= 0:
                self._pop_to(index, tag)
        self.stack.append(tag)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._attributes(tag, attrs)
        if tag in _VOID:
            return
        self._open(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._attributes(tag, attrs)
        if tag in _VOID or self._in_foreign() or tag in _FOREIGN:
            return
        # <div/> is not self-closing in HTML: a browser leaves the div open.
        self._error("self_closed_non_void", tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID:
            if tag != "br":
                self._error("stray_end_tag", tag)
            return
        index = self._find({tag}, set())
        if index < 0:
            for position in range(len(self.force_closed) - 1, -1, -1):
                name, error_index = self.force_closed[position]
                if name == tag:
                    del self.force_closed[position]
                    self.counts["unclosed"] -= 1
                    self.counts["misnested"] += 1
                    if 0 <= error_index < len(self.errors):
                        self.errors[error_index]["kind"] = "misnested"
                    return
            self._error("stray_end_tag", tag)
            return
        if self._in_foreign():
            del self.stack[index:]
            return
        # Elements still open inside the one being closed were never closed
        # (``<h2>x</section>``). If an end tag for one of them comes later,
        # the author closed them in the wrong order instead (``<b><i></b></i>``):
        # that is one misnesting, not an unclosed tag plus a stray one.
        for open_tag in self.stack[index + 1:]:
            if open_tag not in _OPTIONAL_END:
                self.force_closed.append((open_tag, self._error("unclosed", open_tag)))
        del self.stack[index:]

    def finish(self) -> None:
        self.close()
        for tag in self.stack:
            if tag not in _OPTIONAL_END:
                self._error("unclosed", tag)
        self.stack.clear()


def _libxml2_errors(text: str) -> list[dict[str, Any]]:
    try:
        from lxml import etree, html as lxml_html
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise SourceCapabilityError("html.validate requires lxml") from exc
    from .html import strip_xml_declaration

    parser = lxml_html.HTMLParser(recover=True, no_network=True, huge_tree=False)
    try:
        lxml_html.document_fromstring(strip_xml_declaration(text), parser=parser)
    except (etree.ParserError, ValueError):
        pass
    return [
        {"line": int(entry.line), "message": str(entry.message).strip()[:200]}
        for entry in parser.error_log
    ]


class HtmlPathInput(StrictModel):
    """Input naming one HTML artifact.

    Attributes:
        path: Workspace-relative HTML path.
    """

    path: str


class HtmlValidationError(StrictModel):
    """One problem the tag-stack checker found.

    Attributes:
        line: 1-based source line.
        kind: ``unclosed``, ``stray_end_tag``, ``misnested``,
            ``duplicate_attribute`` or ``self_closed_non_void``.
        tag: Element name (``tag[attr]`` for a duplicate attribute).
    """

    line: int
    kind: str
    tag: str


class HtmlParserMessage(StrictModel):
    """One libxml2 HTML parser message.

    Attributes:
        line: 1-based source line.
        message: The parser's message.
    """

    line: int
    message: str


class HtmlValidateOutput(StrictModel):
    """Well-formedness counts for an HTML document.

    Attributes:
        error_count: Sum of the five tag-stack counts below; ``equals 0`` is
            "every tag is closed and nested correctly".
        unclosed_count: Elements whose end tag is required but missing (a
            ``<div>`` never closed; ``<p>``/``<li>``/``<td>``... may omit it).
        stray_end_tag_count: End tags with no open element of that name.
        misnested_count: Elements closed in the wrong order
            (``<b><i></b></i>``): counted once, when the inner element's own
            end tag turns up after the outer one closed it.
        duplicate_attribute_count: Tags naming one attribute twice.
        self_closed_non_void_count: ``<div/>``-style tags on non-void HTML
            elements (a browser leaves them open). SVG/MathML are exempt.
        errors: First 200 problems with line numbers.
        duplicate_ids: ``id`` values used more than once, sorted.
        duplicate_id_count: ``len(duplicate_ids)``.
        has_doctype: Whether a ``<!DOCTYPE ...>`` is present.
        parser_error_count: Messages libxml2's HTML parser logged (an
            independent second reader; its rules are libxml2's, version-bound).
        parser_errors: First 200 of them.
    """

    error_count: int
    unclosed_count: int
    stray_end_tag_count: int
    misnested_count: int
    duplicate_attribute_count: int
    self_closed_non_void_count: int
    errors: list[HtmlValidationError]
    duplicate_ids: list[str]
    duplicate_id_count: int
    has_doctype: bool
    parser_error_count: int
    parser_errors: list[HtmlParserMessage]


def _read_whole(path: Path, limit: int) -> str:
    # The same decoding as every html.* reader: UTF-8, else the page's declared charset (engine review item 13).
    # Imported at call time: html.py imports this module at load.
    from .html import _read_bounded_text

    text, truncated = _read_bounded_text(path, limit)
    if truncated:
        raise SourceDataError("html document exceeds the source content limit")
    return text


def validate_html(text: str) -> HtmlValidateOutput:
    """Run both readers over ``text``."""
    checker = _TagStackChecker()
    checker.feed(text)
    checker.finish()
    counts = checker.counts
    duplicates = sorted(value for value, seen in checker.ids.items() if seen > 1)
    parser_errors = _libxml2_errors(text) if text.strip() else []
    return HtmlValidateOutput(
        error_count=sum(counts.values()),
        unclosed_count=counts["unclosed"],
        stray_end_tag_count=counts["stray_end_tag"],
        misnested_count=counts["misnested"],
        duplicate_attribute_count=counts["duplicate_attribute"],
        self_closed_non_void_count=counts["self_closed_non_void"],
        errors=[HtmlValidationError.model_validate(item) for item in checker.errors],
        duplicate_ids=duplicates,
        duplicate_id_count=len(duplicates),
        has_doctype=checker.has_doctype,
        parser_error_count=len(parser_errors),
        parser_errors=[HtmlParserMessage.model_validate(item) for item in parser_errors[:MAX_REPORTED]],
    )


class Validate(SourceCommand[HtmlPathInput, HtmlValidateOutput]):
    """Count unclosed, stray and misnested tags, duplicate ids and parser errors."""

    name = "validate"
    input_model = HtmlPathInput
    output_model = HtmlValidateOutput

    def run(self, source_input: HtmlPathInput, context: SourceContext) -> HtmlValidateOutput:
        resolved = context.resolve_path(source_input.path)
        return validate_html(_read_whole(resolved, context.max_content_chars))


# --------------------------------------------------------------------------
# html.inspect_css
# --------------------------------------------------------------------------

_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_GRADIENT_RE = re.compile(r"(?i)\b(?:repeating-)?(?:linear|radial|conic)-gradient\s*\(")
_SIDE_BORDER_PROPS = {"border-left", "border-inline-start"}
_SIDE_BORDER_WIDTH_PROPS = {"border-left-width", "border-inline-start-width"}
_SIDE_BORDER_STYLE_PROPS = {"border-left-style", "border-inline-start-style"}
_ZERO_RE = re.compile(r"^0(?:\.0+)?(?:px|em|rem|pt|%)?$")


def _split_top(text: str, separator: str) -> list[str]:
    """Split on ``separator`` outside parentheses and quotes."""
    parts: list[str] = []
    depth, quote, start = 0, "", 0
    for index, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == separator and depth == 0:
            parts.append(text[start:index])
            start = index + 1
    parts.append(text[start:])
    return parts


def _declarations(block: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for item in _split_top(block, ";"):
        if ":" not in item:
            continue
        prop, value = item.split(":", 1)
        prop = prop.strip().lower()
        value = re.sub(r"\s*!important\s*$", "", value.strip(), flags=re.I)
        if prop:
            out.append((prop, value))
    return out


def _rules(css: str) -> list[tuple[str, str]]:
    """(selector, declaration block) pairs, descending into @media/@supports."""
    out: list[tuple[str, str]] = []
    index, length = 0, len(css)
    while index < length:
        open_brace = css.find("{", index)
        if open_brace < 0:
            break
        selector = css[index:open_brace].strip()
        depth, cursor = 1, open_brace + 1
        while cursor < length and depth:
            if css[cursor] == "{":
                depth += 1
            elif css[cursor] == "}":
                depth -= 1
            cursor += 1
        body = css[open_brace + 1:cursor - 1]
        if "{" in body:
            out.extend(_rules(body))
        else:
            out.append((selector, body))
        index = cursor
    return out


def _side_border(prop: str, value: str) -> bool:
    lowered = value.strip().lower()
    if prop in _SIDE_BORDER_PROPS:
        tokens = lowered.split()
        if not tokens or any(token in {"none", "hidden"} for token in tokens):
            return False
        return not any(_ZERO_RE.match(token) for token in tokens) and lowered not in {"initial", "unset", "inherit", "revert"}
    if prop in _SIDE_BORDER_WIDTH_PROPS:
        return bool(lowered) and not _ZERO_RE.match(lowered) and lowered not in {"initial", "unset", "inherit", "revert"}
    if prop in _SIDE_BORDER_STYLE_PROPS:
        return lowered not in {"", "none", "hidden", "initial", "unset", "inherit", "revert"}
    return False


class HtmlCssFinding(StrictModel):
    """One declaration a task may forbid.

    Attributes:
        source: ``style_attribute`` or ``style_element``.
        selector: The rule's selector, or ``tag#id.class`` of the element
            carrying the style attribute.
        property: Lower-cased property name.
        value: Declared value (first 160 characters).
    """

    source: str
    selector: str
    property: str
    value: str


class HtmlInspectCssOutput(StrictModel):
    """Declarations from ``style`` attributes and ``<style>`` elements.

    Linked stylesheets are not fetched (the grader has no network); their count
    is reported so an author knows what was not read.

    Attributes:
        declaration_count: Declarations scanned.
        side_borders: ``border-left`` / ``border-inline-start`` (or their
            ``-width``/``-style`` longhands) that draw a visible side border.
        side_border_count: ``len(side_borders)``.
        gradients: Declarations whose value uses a linear, radial or conic
            gradient (repeating ones included).
        gradient_count: ``len(gradients)``.
        svg_gradient_count: ``<linearGradient>``/``<radialGradient>`` SVG
            elements (reported apart: a chart may use one).
        linked_stylesheet_count: ``<link rel=stylesheet>`` elements not read.
    """

    declaration_count: int
    side_borders: list[HtmlCssFinding]
    side_border_count: int
    gradients: list[HtmlCssFinding]
    gradient_count: int
    svg_gradient_count: int
    linked_stylesheet_count: int


def _element_label(element: Any) -> str:
    label = str(element.tag)
    if element.get("id"):
        label += "#" + element.get("id")
    if element.get("class"):
        label += "." + ".".join(element.get("class").split())
    return label


def inspect_css(text: str) -> HtmlInspectCssOutput:
    """Scan style attributes and ``<style>`` blocks of ``text``."""
    try:
        from lxml import etree, html as lxml_html
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise SourceCapabilityError("html.inspect_css requires lxml") from exc
    if not text.strip():
        return HtmlInspectCssOutput(
            declaration_count=0, side_borders=[], side_border_count=0, gradients=[],
            gradient_count=0, svg_gradient_count=0, linked_stylesheet_count=0,
        )
    from .html import strip_xml_declaration

    parser = lxml_html.HTMLParser(no_network=True, remove_comments=True, huge_tree=False)
    try:
        root = lxml_html.document_fromstring(strip_xml_declaration(text), parser=parser)
    except (etree.ParserError, ValueError) as exc:
        raise SourceDataError("html document is empty or cannot be parsed") from exc
    found: list[tuple[str, str, str, str]] = []
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        style = element.get("style")
        if style:
            for prop, value in _declarations(_COMMENT_RE.sub("", style)):
                found.append(("style_attribute", _element_label(element), prop, value))
    for element in root.iter("style"):
        css = _COMMENT_RE.sub("", element.text_content() or "")
        for selector, block in _rules(css):
            for prop, value in _declarations(block):
                found.append(("style_element", " ".join(selector.split())[:160], prop, value))
    side, gradients = [], []
    for source, selector, prop, value in found:
        finding = HtmlCssFinding(source=source, selector=selector, property=prop, value=value[:160])
        if _side_border(prop, value):
            side.append(finding)
        if _GRADIENT_RE.search(value):
            gradients.append(finding)
    svg_gradients = sum(
        1 for element in root.iter()
        if isinstance(element.tag, str)
        and element.tag.rsplit("}", 1)[-1].lower() in {"lineargradient", "radialgradient"}
    )
    linked = sum(
        1 for element in root.iter("link")
        if "stylesheet" in (element.get("rel") or "").lower().split()
    )
    return HtmlInspectCssOutput(
        declaration_count=len(found),
        side_borders=side[:MAX_REPORTED], side_border_count=len(side),
        gradients=gradients[:MAX_REPORTED], gradient_count=len(gradients),
        svg_gradient_count=svg_gradients, linked_stylesheet_count=linked,
    )


class InspectCss(SourceCommand[HtmlPathInput, HtmlInspectCssOutput]):
    """List side-border and gradient declarations in inline and embedded CSS."""

    name = "inspect_css"
    input_model = HtmlPathInput
    output_model = HtmlInspectCssOutput

    def run(self, source_input: HtmlPathInput, context: SourceContext) -> HtmlInspectCssOutput:
        resolved = context.resolve_path(source_input.path)
        return inspect_css(_read_whole(resolved, context.max_content_chars))


# --------------------------------------------------------------------------
# html.read_table
# --------------------------------------------------------------------------


class HtmlReadTableInput(StrictModel):
    """Input for ``html.read_table``.

    Attributes:
        path: Workspace-relative HTML path.
        selector: CSS selector that must match exactly one ``<table>``
            (``#findings``, ``table.summary``).
        header_match: Optional regex tried against each row rendered as
            ``cell|cell|...``; the first match is the header row. Without it
            the first row of ``<thead>`` (else of the table) is the header.
        link_targets: When True, a cell holding links reads as its text
            followed by each ``<a href>`` target, so an id that lives only in a
            link can key a row. Default False: text only.
    """

    path: str
    selector: str = Field(min_length=1, max_length=500)
    header_match: str | None = None
    link_targets: bool = False

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


class HtmlReadTableOutput(RootModel[list[dict[str, str]]]):
    """One header-keyed mapping per data row (``docx.read_table`` shape), so
    ``table_equals`` grades it. Cell text is what a reader sees (tags
    stripped, entities decoded, whitespace collapsed); hidden rows are gone;
    ``colspan``/``rowspan`` cells are repeated into every grid slot they cover."""


def _table_grid(table: Any, element_text: Any) -> tuple[list[list[str]], int]:
    """Rows of the table's own grid (nested tables excluded) and the index of
    the first ``<thead>`` row (-1 when there is none)."""
    rows = table.xpath("./tr|./thead/tr|./tbody/tr|./tfoot/tr")
    thead_first = next(
        (i for i, row in enumerate(rows) if row.getparent().tag == "thead"), -1
    )
    grid: list[list[str]] = []
    carry: dict[int, tuple[str, int]] = {}
    for row in rows:
        cells = row.xpath("./td|./th")
        out: list[str] = []
        column = 0
        queue = list(cells)
        while queue or column in carry:
            if column in carry:
                text, remaining = carry[column]
                out.append(text)
                if remaining <= 1:
                    del carry[column]
                else:
                    carry[column] = (text, remaining - 1)
                column += 1
                continue
            cell = queue.pop(0)
            text = element_text(cell)
            try:
                colspan = max(1, min(100, int(cell.get("colspan") or 1)))
                rowspan = max(1, min(1000, int(cell.get("rowspan") or 1)))
            except ValueError:
                colspan, rowspan = 1, 1
            for _ in range(colspan):
                out.append(text)
                if rowspan > 1:
                    carry[column] = (text, rowspan - 1)
                column += 1
        grid.append(out)
    return grid, thead_first


def read_html_table(
    text: str, selector: str, header_match: str | None, link_targets: bool = False
) -> list[dict[str, str]]:
    """Header-keyed rows of the one table ``selector`` matches."""
    try:
        from cssselect import SelectorError
        from lxml.cssselect import CSSSelector
    except ImportError as exc:  # pragma: no cover - dependencies are declared
        raise SourceCapabilityError("html.read_table requires lxml and cssselect") from exc
    from .html import _element_text, _parse_html

    try:
        compiled = CSSSelector(selector)
    except SelectorError as exc:
        raise SourceAuthoringError(f"invalid CSS selector: {exc}") from exc
    if not text.strip():
        raise SourceDataError("html document is empty")
    root = _parse_html(text)
    tables = [node for node in compiled(root) if str(node.tag).lower() == "table"]
    if len(tables) != 1:
        raise SourceDataError(f"selector {selector!r} matched {len(tables)} tables, expected exactly 1")
    def cell_text(cell: Any) -> str:
        base = _element_text(cell)
        if not link_targets:
            return base
        hrefs = [a.get("href").strip() for a in cell.iter("a") if (a.get("href") or "").strip()]
        return " ".join([base] + hrefs).strip()

    grid, thead_first = _table_grid(tables[0], cell_text)
    if not grid:
        return []
    header_row = thead_first if thead_first >= 0 else 0
    if header_match:
        pattern = re.compile(header_match)
        header_row = next((i for i, row in enumerate(grid) if pattern.search("|".join(row))), -1)
        if header_row < 0:
            raise SourceDataError(f"no table row matches header_match {header_match!r}")
    keys: list[str] = []
    for position, cell in enumerate(grid[header_row]):
        key = cell or f"column_{position + 1}"
        keys.append(key if key not in keys else f"{key} ({position + 1})")
    rows: list[dict[str, str]] = []
    for row in grid[header_row + 1:]:
        if not any(cell.strip() for cell in row):
            continue
        record = {(keys[i] if i < len(keys) else f"column_{i + 1}"): cell for i, cell in enumerate(row)}
        for key in keys[len(row):]:
            record[key] = ""
        rows.append(record)
    return rows


class ReadTable(SourceCommand[HtmlReadTableInput, HtmlReadTableOutput]):
    """Read one HTML table, chosen by CSS selector, as header-keyed rows."""

    name = "read_table"
    input_model = HtmlReadTableInput
    output_model = HtmlReadTableOutput

    def run(self, source_input: HtmlReadTableInput, context: SourceContext) -> HtmlReadTableOutput:
        resolved = context.resolve_path(source_input.path)
        text = _read_whole(resolved, context.max_content_chars)
        return HtmlReadTableOutput(read_html_table(
            text, source_input.selector, source_input.header_match, source_input.link_targets
        ))


HTML_CHECK_COMMANDS = (Validate(), InspectCss(), ReadTable())
