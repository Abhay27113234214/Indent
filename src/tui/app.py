import time
import shutil
import subprocess
import random
from rich.live import Live
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
from .console import console, print_welcome, print_goodbye, COLORS
from .prompt import get_session


class IndentCLI:
    def __init__(self):
        self.session = get_session()
        self.running = False
        self.turn_count = 0

    def run(self):
        import sys
        
        print_welcome()

        console.print(f"\n[{COLORS['yellow']}]Do you grant permission to analyze the workspace?[/{COLORS['yellow']}]")
        permission = input(" (y/n) > ").strip().lower()
        
        if permission not in ['y', 'yes']:
            print("we need permission to analyze the code base to work")
            sys.exit(0)
            
        from backend.graph import indent_graph
        
        config = {"configurable": {"thread_id": "session_1"}}
        
        with console.status(f"[{COLORS['dim']}]Running workspace_analyzer node...[/{COLORS['dim']}]", spinner="dots"):
            state = indent_graph.invoke({"messages": []}, config=config)
            
        console.print(f"[{COLORS['green']}]Workspace analyzed successfully![/{COLORS['green']}]")
        
        ctx = state.get("workspace_context")
        if ctx:
            console.print(f"  [{COLORS['dim']}]Detected stack: {', '.join(ctx.tech_stack)}[/{COLORS['dim']}]\n")

        self.running = True

        while self.running:
            try:
                user_input = self.session.prompt()

                if not user_input.strip():
                    continue

                self.handle_input(user_input)

            except KeyboardInterrupt:
                continue
            except EOFError:
                print_goodbye()
                break


    def handle_input(self, text: str):
        text = text.strip()
        if text.startswith('/'):
            self.handle_command(text)
        elif text.startswith('!'):
            self.handle_bash(text)
        else:
            self.process_chat(text)

    def handle_bash(self, text: str):
        cmd = text[1:].strip()

        console.print(f"[{COLORS['red']} bold]![/{COLORS['red']} bold] [{COLORS['red']}]{cmd}[/{COLORS['red']}]")

        if cmd:
            try:
                result = subprocess.run(["bash", "-c", cmd], text=True, capture_output=True)

                if result.stdout:
                    console.print(
                        Syntax(
                            result.stdout.rstrip(),
                            "bash",
                            theme="dracula",
                            line_numbers=False,
                            padding=1,
                        )
                    )
                if result.stderr:
                    console.print(f"[{COLORS['red']}]{result.stderr.rstrip()}[/{COLORS['red']}]")

            except Exception as e:
                console.print(f"[{COLORS['red']} bold]Error:[/{COLORS['red']} bold] [{COLORS['red']}]{str(e)}[/{COLORS['red']}]")

        self._print_divider()


    def handle_command(self, text: str):
        console.print(f"[{COLORS['green']} bold]>>[/{COLORS['green']} bold] [{COLORS['green']}]{text}[/{COLORS['green']}]")

        cmd = text.lower()
        if cmd in ('/quit', '/exit'):
            self.running = False
            print_goodbye()
        elif cmd == '/help':
            self._print_help()
        elif cmd == '/clear':
            console.clear()
            print_welcome()
        else:
            console.print(f"[{COLORS['red']}]Unknown command: {cmd}[/{COLORS['red']}]")

        self._print_divider()

    def _print_help(self):
        """Render a beautiful help table."""
        help_table = Table(
            show_header=True,
            header_style=f"bold {COLORS['cyan']}",
            border_style=COLORS["bg_line"],
            padding=(0, 2),
            title=f"[bold {COLORS['white']}]Available Commands[/bold {COLORS['white']}]",
            title_style=f"bold {COLORS['white']}",
        )
        help_table.add_column("Command",     style=f"{COLORS['green']} bold", min_width=12)
        help_table.add_column("Description", style=COLORS["white"])

        help_table.add_row("/help",   "Show this help message")
        help_table.add_row("/clear",  "Clear screen and show the welcome banner")
        help_table.add_row("/quit",   "Exit Indent")
        help_table.add_row("!<cmd>",  "Run a bash command (e.g. !ls -la)")

        console.print(help_table)


    def process_chat(self, text: str):
        self.turn_count += 1

        console.print(f"[{COLORS['green']} bold]>>[/{COLORS['green']} bold] [{COLORS['green']}]{text}[/{COLORS['green']}]")

        start_time = time.time()

        self._animate_thinking()

        mock_response = (
            "I have received your request and am analyzing the context.\n\n"
            "Since I am designed as an **Agentic AI Platform**, "
            "I will be able to perform terminal actions, write files, and integrate seamlessly.\n\n"
            "```python\n"
            "# I am generating some Python code live for you!\n"
            "def execute_task(task_name: str):\n"
            "    print(f'Executing: {task_name}')\n"
            "    return True\n"
            "```\n\n"
            "What's our next step?"
        )

        self._stream_response(mock_response)

        elapsed = time.time() - start_time
        token_estimate = len(mock_response.split())
        console.print(
            f"  [{COLORS['dim']}]⏱ {elapsed:.1f}s  •  "
            f"~{token_estimate} tokens  •  "
            f"gemini-3.1-pro[/{COLORS['dim']}]"
        )

        self._print_divider(f"turn {self.turn_count}")


    def _animate_thinking(self):
        """Cycle through multiple thinking phases with different spinners."""
        phases = [
            ("dots",  "Reading context..."),
            ("dots2", "Analyzing request..."),
            ("dots3", "Generating response..."),
        ]
        for spinner, message in phases:
            with console.status(
                f" [{COLORS['dim']}]{message}[/{COLORS['dim']}]",
                spinner=spinner,
                spinner_style=COLORS["cyan"],
            ):
                time.sleep(0.4)


    def _stream_response(self, response: str):
        """
        Stream text character-by-character with:
        - A blinking block cursor (█) that chases the text
        - Dracula syntax highlighting for code blocks
        - A cyan > bullet on the left
        """
        chars_yielded = 0
        chunk = ""

        try:
            with Live(console=console, refresh_per_second=30) as live:
                while chars_yielded < len(response):
                    chars_yielded = min(chars_yielded + random.randint(2, 6), len(response))
                    chunk = response[:chars_yielded]

                    cursor = " █"

                    grid = Table.grid(padding=(0, 2))
                    grid.add_column()
                    grid.add_column()
                    grid.add_row(
                        f"[{COLORS['cyan']} bold]>[/{COLORS['cyan']} bold]",
                        Markdown(chunk + cursor, code_theme="dracula"),
                    )

                    live.update(grid)
                    time.sleep(random.uniform(0.01, 0.04))

                grid = Table.grid(padding=(0, 2))
                grid.add_column()
                grid.add_column()
                grid.add_row(
                    f"[{COLORS['cyan']} bold]>[/{COLORS['cyan']} bold]",
                    Markdown(response, code_theme="dracula"),
                )
                live.update(grid)

        except KeyboardInterrupt:
            chunk += "\n*(Output interrupted)*"
            grid = Table.grid(padding=(0, 2))
            grid.add_column()
            grid.add_column()
            grid.add_row(
                f"[{COLORS['cyan']} bold]>[/{COLORS['cyan']} bold]",
                Markdown(chunk, code_theme="dracula"),
            )
            console.print(grid)


    def _print_divider(self, label: str = ""):
        """Print a thick divider using ━ with an optional centered label."""
        width = shutil.get_terminal_size().columns

        if label:
            label_str = f" {label} "
            side = (width - len(label_str)) // 2
            left = "━" * side
            right = "━" * (width - side - len(label_str))

            divider = Text()
            divider.append(left, style=COLORS["bg_line"])
            divider.append(label_str, style=COLORS["dim"])
            divider.append(right, style=COLORS["bg_line"])
            console.print(divider)
        else:
            console.print(Text("━" * width, style=COLORS["bg_line"]))
