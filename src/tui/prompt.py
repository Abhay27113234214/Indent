import shutil
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.keys import Keys
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.application import get_app
from pathlib import Path

prompt_style = Style.from_dict({
    'prompt':      '#00e5ff bold',
    'prompt_bash': '#ff5555 bold',

    'box':       '#6272a4',
    'separator': '#6272a4',
    'hint':      '#6272a4 italic',

    'input':      '#50fa7b',
    'input_bash': '#ff5555',

    'bottom-toolbar':      'bg:#282a36 #6272a4',
    'bottom-toolbar.text': 'bg:#282a36 #6272a4',

    'completion-menu':                    'bg:#282a36 #f8f8f2',
    'completion-menu.completion':         'bg:#282a36 #f8f8f2',
    'completion-menu.completion.current': 'bg:#44475a #50fa7b bold',
    'completion-menu.meta':               'bg:#282a36 #6272a4 italic',
    'completion-menu.meta.current':       'bg:#44475a #bd93f9 italic',
})


class SlashCommandCompleter(Completer):
    """Only triggers autocomplete when the user explicitly types '/' at the start."""
    COMMANDS = {
        '/help':  'Show available commands',
        '/clear': 'Clear screen',
        '/quit':  'Exit Indent',
        '/exit':  'Exit Indent',
    }

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith('/'):
            for cmd, desc in self.COMMANDS.items():
                if cmd.startswith(text.lower()):
                    yield Completion(cmd, start_position=-len(text), display_meta=desc)


def create_keybindings():
    kb = KeyBindings()

    @kb.add(Keys.Enter)
    def _(event):
        event.current_buffer.validate_and_handle()

    @kb.add(Keys.Escape, '[', '1', '3', ';', '2', 'u')
    @kb.add('escape', 'enter')
    def _(event):
        event.current_buffer.insert_text('\n')

    return kb


class DynamicLexer(Lexer):
    """Dynamically syntax-highlights the input line based on bash mode."""
    def lex_document(self, document):
        def get_line(lineno):
            style = 'class:input_bash' if document.text.startswith('!') else 'class:input'
            return [(style, document.lines[lineno])]
        return get_line


def is_bash_mode():
    """Check if the user is currently in bash mode (typing starts with !)."""
    app = get_app()
    if app and hasattr(app, 'current_buffer'):
        return app.current_buffer.text.startswith('!')
    return False


def get_prompt_message():
    """
    Draws a full-width horizontal rule above the input area,
    and dynamically switches the bullet based on bash mode.
    """
    width = shutil.get_terminal_size().columns
    top_line = '╭' + ('─' * (width - 2))

    if is_bash_mode():
        return HTML(f'<box>{top_line}</box>\n<box>│</box> ')
    return HTML(f'<box>{top_line}</box>\n<box>│</box> <prompt>❯❯</prompt> ')


def get_prompt_continuation(width, line_number, is_soft_wrap):
    """Continuation prompt for multiline input."""
    return HTML('<box>│</box> <separator>⋯</separator> ')


def get_bottom_toolbar():
    """
    Draws a full-width bottom rule with mode-specific hints
    embedded directly into the line.
    """
    width = shutil.get_terminal_size().columns

    if is_bash_mode():
        text = ' ⚡ BASH  •  Enter to execute '
        color = '#ff5555'
    else:
        text = ' Enter send  •  Alt+Enter new line  •  / commands  •  ! bash '
        color = '#6272a4'

    left_line = '╰' + ('─' * 3)
    right_len = width - len(text) - len(left_line) - 1
    right_line = '─' * max(0, right_len)

    return HTML(
        f'<box>{left_line}</box>'
        f'<style fg="{color}"><b>{text}</b></style>'
        f'<box>{right_line}</box>'
    )


def get_session():
    """Create and return a fully configured prompt_toolkit session."""
    history_file = Path.home() / '.indent_history'

    return PromptSession(
        message=get_prompt_message,
        style=prompt_style,
        multiline=True,
        history=FileHistory(str(history_file)),
        completer=SlashCommandCompleter(),
        key_bindings=create_keybindings(),
        bottom_toolbar=get_bottom_toolbar,
        prompt_continuation=get_prompt_continuation,
        erase_when_done=True,
        lexer=DynamicLexer(),
    )
