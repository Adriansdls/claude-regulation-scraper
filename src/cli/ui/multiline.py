"""Multi-line input with visual feedback.

Enhanced input handling for complex queries.
"""

from typing import Optional, Callable
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import Completer

try:
    from pygments.lexers.python import PythonLexer
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


class MultilinePrompt:
    """Enhanced prompt supporting multi-line input."""

    def __init__(
        self,
        completer: Optional[Completer] = None,
        enable_multiline_mode: bool = True,
        multiline_trigger: str = "\\"
    ):
        """
        Initialize multi-line prompt.

        Args:
            completer: Completer for autocomplete
            enable_multiline_mode: Enable multi-line mode
            multiline_trigger: Character to trigger multi-line mode
        """
        self.completer = completer
        self.enable_multiline_mode = enable_multiline_mode
        self.multiline_trigger = multiline_trigger
        self.in_multiline = False

        # Create key bindings
        self.bindings = self._create_key_bindings()

        # Create custom style
        self.style = Style.from_dict({
            'prompt': 'cyan bold',
            'continuation': 'cyan',
        })

    def _create_key_bindings(self) -> KeyBindings:
        """Create custom key bindings."""
        bindings = KeyBindings()

        # Ctrl+J to toggle multi-line mode
        @bindings.add(Keys.ControlJ)
        def _(event):
            """Toggle multi-line mode."""
            self.in_multiline = not self.in_multiline

            if self.in_multiline:
                event.app.current_buffer.insert_text("\n")

        # Ctrl+D in multi-line mode submits
        @bindings.add(Keys.ControlD)
        def _(event):
            """Submit in multi-line mode."""
            if self.in_multiline:
                event.app.current_buffer.validate_and_handle()

        return bindings

    def get_prompt_message(self) -> HTML:
        """Get prompt message based on mode."""
        if self.in_multiline:
            return HTML('<prompt>... </prompt>')
        else:
            return HTML('<prompt>You: </prompt>')

    def prompt(self, message: str = "You: ") -> str:
        """
        Get input from user.

        Args:
            message: Prompt message

        Returns:
            User input
        """
        # Check if input starts with multiline trigger
        session = PromptSession(
            completer=self.completer,
            key_bindings=self.bindings,
            style=self.style,
            enable_history_search=True,
            multiline=False,  # Start in single-line mode
        )

        # Get first line
        first_line = session.prompt(message)

        # Check for multiline trigger
        if self.enable_multiline_mode and first_line.endswith(self.multiline_trigger):
            return self._multiline_input(first_line[:-1])  # Remove trigger
        else:
            return first_line

    def _multiline_input(self, first_line: str) -> str:
        """
        Handle multi-line input.

        Args:
            first_line: First line of input

        Returns:
            Complete multi-line input
        """
        lines = [first_line] if first_line.strip() else []

        session = PromptSession(
            multiline=True,
            prompt_continuation=lambda width, line_number, is_soft_wrap: "... ",
            style=self.style,
        )

        print("[Multi-line mode - Press Ctrl+D or Meta+Enter to submit]")

        rest = session.prompt("")
        if rest.strip():
            lines.append(rest)

        return "\n".join(lines)


async def async_multiline_prompt(
    message: str = "You: ",
    completer: Optional[Completer] = None,
    multiline_trigger: str = "\\",
    history = None
) -> str:
    """
    Async multi-line prompt.

    Args:
        message: Prompt message
        completer: Completer instance
        multiline_trigger: Trigger character for multi-line
        history: History instance

    Returns:
        User input
    """
    session = PromptSession(
        message=message,
        completer=completer,
        multiline=False,
        enable_history_search=True,
        history=history,
    )

    # Get first line
    first_line = await session.prompt_async()

    # Check for multiline trigger
    if first_line.strip().endswith(multiline_trigger):
        # Enter multi-line mode
        lines = [first_line[:-1]]  # Remove trigger

        multiline_session = PromptSession(
            message="... ",
            multiline=True,
            prompt_continuation=lambda w, l, s: "... ",
        )

        print("[dim](Multi-line mode - Press Esc+Enter or Ctrl+D to submit)[/dim]")

        rest = await multiline_session.prompt_async()
        if rest.strip():
            lines.append(rest)

        return "\n".join(lines)
    else:
        return first_line


class QueryBuilder:
    """Interactive query builder with templates."""

    def __init__(self):
        """Initialize query builder."""
        self.templates = {
            "gaps": "Find gaps in the {topic} literature",
            "communities": "Detect communities using {algorithm} algorithm",
            "centrality": "Calculate {metric} centrality for papers",
            "paths": "Find paths between {concept1} and {concept2}",
            "authors": "Analyze {author} collaboration patterns",
            "trends": "Show research trends for {topic} over time",
        }

    def build_query(self, template_name: str, **kwargs) -> str:
        """
        Build query from template.

        Args:
            template_name: Template to use
            **kwargs: Template variables

        Returns:
            Filled template
        """
        template = self.templates.get(template_name, "")

        for key, value in kwargs.items():
            template = template.replace(f"{{{key}}}", value)

        return template

    def list_templates(self) -> list[str]:
        """List available templates."""
        return list(self.templates.keys())


def create_interactive_prompt(
    message: str = "You: ",
    completer: Optional[Completer] = None,
    enable_syntax_highlighting: bool = False,
    history = None
) -> PromptSession:
    """
    Create interactive prompt session.

    Args:
        message: Prompt message
        completer: Completer instance
        enable_syntax_highlighting: Enable syntax highlighting
        history: History instance

    Returns:
        Configured prompt session
    """
    lexer = None
    if enable_syntax_highlighting and PYGMENTS_AVAILABLE:
        lexer = PygmentsLexer(PythonLexer)

    session = PromptSession(
        message=message,
        completer=completer,
        lexer=lexer,
        enable_history_search=True,
        history=history,
        multiline=False,
        wrap_lines=True,
    )

    return session
