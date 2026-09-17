import os
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
    'prompt': '#00e5ff bold',
    'prompt_bash': '#ff5555 bold',
    'separator': '#6272a4',
    'bottom-toolbar': '#6272a4 italic',
    'box': '#6272a4',
    'input': '#50fa7b',
    'input_bash': '#ff5555',
})

class SlashCommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith('/'):
            commands = ['/help', '/clear', '/quit', '/exit']
            for cmd in commands:
                if cmd.startswith(text.lower()):
                    yield Completion(cmd, start_position=-len(text))

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
    app = get_app()
    if app and hasattr(app, 'current_buffer'):
        return app.current_buffer.text.startswith('!')
    return False

def get_prompt_message():
    """Dynamically switch the prompt bullet if bash mode is active."""
    if is_bash_mode():
        return HTML('<box>╭─</box>\n<box>│</box> ')
    return HTML('<box>╭─</box>\n<box>│</box> <prompt>❯❯</prompt> ')

def get_bottom_toolbar():
    """Dynamically switch the toolbar instructions if bash mode is active."""
    if is_bash_mode():
        return HTML('<box>╰─</box> <style fg="#ff5555"><i> Bash Mode: Enter and run a bash command</i></style>')
    return HTML('<box>╰─</box> <i>Enter to send • Alt+Enter for new line</i>')

def get_session():
    history_file = Path.home() / '.indent_history'
    
    return PromptSession(
        message=get_prompt_message,
        style=prompt_style,
        multiline=True,
        history=FileHistory(str(history_file)),
        completer=SlashCommandCompleter(),
        key_bindings=create_keybindings(),
        bottom_toolbar=get_bottom_toolbar,
        prompt_continuation=HTML('<box>│</box> <separator>⋯</separator> '),
        erase_when_done=True,
        lexer=DynamicLexer()
    )
