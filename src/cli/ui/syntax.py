"""Enhanced syntax highlighting for code and data.

Use Pygments for beautiful syntax highlighting in terminal output.
"""

from typing import Optional
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
import re

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer
    from pygments.formatters import TerminalFormatter, Terminal256Formatter
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


class CodeHighlighter:
    """Syntax highlighting for code blocks."""

    def __init__(
        self,
        console: Optional[Console] = None,
        theme: str = "monokai",
        line_numbers: bool = True
    ):
        """
        Initialize highlighter.

        Args:
            console: Rich console instance
            theme: Syntax theme
            line_numbers: Show line numbers
        """
        self.console = console or Console()
        self.theme = theme
        self.line_numbers = line_numbers

    def highlight_code(
        self,
        code: str,
        language: str = "python",
        title: Optional[str] = None
    ) -> None:
        """
        Highlight and print code.

        Args:
            code: Code to highlight
            language: Programming language
            title: Optional title for code block
        """
        syntax = Syntax(
            code,
            language,
            theme=self.theme,
            line_numbers=self.line_numbers,
            word_wrap=False
        )

        if title:
            panel = Panel(syntax, title=title, border_style="blue")
            self.console.print(panel)
        else:
            self.console.print(syntax)

    def highlight_json(self, json_str: str, title: Optional[str] = None):
        """Highlight JSON."""
        self.highlight_code(json_str, language="json", title=title)

    def highlight_python(self, code: str, title: Optional[str] = None):
        """Highlight Python code."""
        self.highlight_code(code, language="python", title=title)

    def highlight_networkx(self, code: str, title: Optional[str] = None):
        """Highlight NetworkX code (Python)."""
        self.highlight_code(
            code,
            language="python",
            title=title or "NetworkX Code"
        )

    def detect_and_highlight(self, text: str) -> str:
        """
        Detect code blocks in text and highlight them.

        Args:
            text: Text potentially containing code blocks

        Returns:
            Text with highlighted code blocks
        """
        # Pattern for code blocks: ```language\ncode\n```
        pattern = r"```(\w+)?\n(.*?)```"

        def replace_code_block(match):
            language = match.group(1) or "python"
            code = match.group(2)

            if not PYGMENTS_AVAILABLE:
                return f"\n{code}\n"

            try:
                lexer = get_lexer_by_name(language)
                formatter = Terminal256Formatter()
                highlighted = highlight(code, lexer, formatter)
                return f"\n{highlighted}"
            except Exception:
                return f"\n{code}\n"

        return re.sub(pattern, replace_code_block, text, flags=re.DOTALL)


class ResponseFormatter:
    """Format agent responses with syntax highlighting."""

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize formatter.

        Args:
            console: Rich console instance
        """
        self.console = console or Console()
        self.highlighter = CodeHighlighter(console=console)

    def format_response(self, text: str) -> str:
        """
        Format response text with highlighting.

        Args:
            text: Response text

        Returns:
            Formatted text
        """
        # Detect and highlight code blocks
        formatted = self.highlighter.detect_and_highlight(text)

        # Highlight inline code (`code`)
        formatted = self._highlight_inline_code(formatted)

        return formatted

    def _highlight_inline_code(self, text: str) -> str:
        """Highlight inline code with backticks."""
        # Pattern for inline code: `code`
        pattern = r"`([^`]+)`"

        def replace_inline(match):
            code = match.group(1)
            return f"[cyan]{code}[/cyan]"

        return re.sub(pattern, replace_inline, text)

    def format_tool_result(self, result: dict) -> str:
        """
        Format tool result for display.

        Args:
            result: Tool result dictionary

        Returns:
            Formatted string
        """
        lines = []

        # Success status
        if result.get("success"):
            lines.append("[green]✓[/green] Success")
        else:
            lines.append("[red]✗[/red] Failed")

        # Main result
        if "result" in result and result["result"]:
            lines.append(f"\nResult: {result['result']}")

        # Interpretation
        if "interpretation" in result:
            lines.append(f"\n[dim]{result['interpretation']}[/dim]")

        # Display (for visualizations)
        if "display" in result:
            lines.append(f"\n{result['display']}")

        # Error
        if "error" in result:
            lines.append(f"\n[red]Error: {result['error']}[/red]")

        return "\n".join(lines)


def highlight_query_template(template: str) -> str:
    """
    Highlight query template placeholders.

    Args:
        template: Query template with {placeholders}

    Returns:
        Highlighted template
    """
    # Highlight {placeholders} in cyan
    pattern = r"\{([^}]+)\}"

    def replace_placeholder(match):
        placeholder = match.group(1)
        return f"[cyan]{{{placeholder}}}[/cyan]"

    return re.sub(pattern, replace_placeholder, template)


def create_code_comparison(
    code1: str,
    code2: str,
    title1: str = "Before",
    title2: str = "After",
    language: str = "python"
):
    """
    Display side-by-side code comparison.

    Args:
        code1: First code block
        code2: Second code block
        title1: Title for first block
        title2: Title for second block
        language: Programming language
    """
    from rich.columns import Columns
    from rich.panel import Panel

    syntax1 = Syntax(code1, language, theme="monokai", line_numbers=True)
    syntax2 = Syntax(code2, language, theme="monokai", line_numbers=True)

    panel1 = Panel(syntax1, title=title1, border_style="red")
    panel2 = Panel(syntax2, title=title2, border_style="green")

    console = Console()
    console.print(Columns([panel1, panel2], equal=True))


def highlight_diff(diff_text: str):
    """
    Highlight diff output.

    Args:
        diff_text: Diff text
    """
    console = Console()

    lines = diff_text.split("\n")
    for line in lines:
        if line.startswith("+"):
            console.print(line, style="green")
        elif line.startswith("-"):
            console.print(line, style="red")
        elif line.startswith("@"):
            console.print(line, style="cyan")
        else:
            console.print(line, style="dim")
