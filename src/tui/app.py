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
            console.print(f"  [{COLORS['cyan']}]● Summary:   [/{COLORS['cyan']}][{COLORS['dim']}]{ctx.summary}[/{COLORS['dim']}]")
            console.print(f"  [{COLORS['purple']}]● Stack:     [/{COLORS['purple']}][{COLORS['dim']}]{', '.join(ctx.tech_stack)}[/{COLORS['dim']}]")
            console.print(f"  [{COLORS['green']}]● Prediction:[/{COLORS['green']}][{COLORS['dim']}] {ctx.project_prediction}[/{COLORS['dim']}]\n")

        self.running = True

        while self.running:
            try:
                console.print(f"\n[{COLORS['dim']}]What would you like to build or modify?[/{COLORS['dim']}]")
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


    def _get_user_answer(self, q_idx: int, question: str) -> str:
        """Prompts for an answer, allowing the user to seamlessly execute / or ! commands."""
        from .prompt import set_prompt_prefix
        
        console.print(f"[{COLORS['yellow']}]Q{q_idx}: {question}[/{COLORS['yellow']}]")
        
        set_prompt_prefix(f"A{q_idx}:")
        
        try:
            while True:
                ans = self.session.prompt().strip()
                if not ans:
                    continue
                    
                if ans.startswith('/'):
                    self.handle_command(ans)
                    if not self.running:
                        raise EOFError()
                    console.print(f"\n[{COLORS['yellow']}]Q{q_idx}: {question}[/{COLORS['yellow']}]")
                elif ans.startswith('!'):
                    self.handle_bash(ans)
                    console.print(f"\n[{COLORS['yellow']}]Q{q_idx}: {question}[/{COLORS['yellow']}]")
                else:
                    return ans
        finally:
            set_prompt_prefix("❯❯")

    def process_chat(self, text: str):
        from langgraph.types import Command
        from backend.graph import indent_graph
        
        self.turn_count += 1
        console.print(f"[{COLORS['green']} bold]>>[/{COLORS['green']} bold] [{COLORS['green']}]{text}[/{COLORS['green']}]")
        
        start_time = time.time()
        config = {"configurable": {"thread_id": "session_1"}}
        
        with console.status(f"[{COLORS['cyan']}]Analyzing and planning...[/{COLORS['cyan']}]", spinner="dots"):
            indent_graph.invoke({"user_query": text}, config=config)
            
        snapshot = indent_graph.get_state(config)
        
        while snapshot.next and snapshot.tasks and snapshot.tasks[0].interrupts:
            interrupt_data = snapshot.tasks[0].interrupts[0].value
            int_type = interrupt_data.get("type")
            
            if int_type == "ask_questions":
                questions = interrupt_data.get("questions", [])
                console.print(f"\n[{COLORS['yellow']} bold]Clarification Required:[/{COLORS['yellow']} bold]")
                answers = []
                for i, q in enumerate(questions):
                    ans = self._get_user_answer(i + 1, q)
                    answers.append(ans)
                resume_payload = answers
                status_msg = "Updating architectural plan..."
                
            elif int_type == "ask_approval":
                plan = interrupt_data.get("plan", "")
                console.print(f"\n[{COLORS['purple']} bold]Proposed Execution Plan:[/{COLORS['purple']} bold]")
                console.print(Markdown(plan, code_theme="dracula"))
                
                console.print(f"\n[{COLORS['yellow']}]Do you approve this plan? (Y/n)[/{COLORS['yellow']}]")
                from .prompt import set_prompt_prefix
                set_prompt_prefix("Approval:")
                try:
                    while True:
                        decision = self.session.prompt().strip().lower()
                        if decision in ['y', 'yes', '']:
                            resume_payload = True
                            break
                        elif decision in ['n', 'no']:
                            resume_payload = False
                            break
                finally:
                    set_prompt_prefix("❯❯")
                status_msg = "Executing approved plan and generating code..."
                
            elif int_type == "ask_feedback":
                console.print(f"\n[{COLORS['yellow']} bold]Plan Rejected.[/{COLORS['yellow']} bold]")
                console.print(f"[{COLORS['yellow']}]Why do you reject this plan? What should change?[/{COLORS['yellow']}]")
                
                from .prompt import set_prompt_prefix
                set_prompt_prefix("Feedback:")
                try:
                    resume_payload = self.session.prompt().strip()
                finally:
                    set_prompt_prefix("❯❯")
                status_msg = "Drafting alternative architecture..."
                
            with console.status(f"[{COLORS['cyan']}]{status_msg}[/{COLORS['cyan']}]", spinner="dots2"):
                indent_graph.invoke(Command(resume=resume_payload), config=config)
                
            snapshot = indent_graph.get_state(config)
            
        final_plan = snapshot.values.get("plan")
        is_approved = snapshot.values.get("is_approved")
        file_edits = snapshot.values.get("file_edits", [])
        
        if is_approved and file_edits:
            console.print(f"\n[{COLORS['green']} bold]Execution Complete! Modified Files:[/{COLORS['green']} bold]")
            from rich.table import Table
            table = Table(show_header=False, box=None, padding=(0, 2))
            for edit in file_edits:
                action = edit.get('action', '').upper()
                path = edit.get('file_path', '')
                color = "green" if action == "NEW" else "cyan" if action == "REPLACE" else "yellow"
                table.add_row(f"[{color}]{action}[/{color}]", path)
            console.print(table)
        elif is_approved:
            console.print(f"\n[{COLORS['green']} bold]Plan Approved! Setup complete. (No file edits required)[/{COLORS['green']} bold]")
        elif final_plan == "":
            console.print(f"\n[{COLORS['red']}]Please be precise on your next request. Let's start anew.[/{COLORS['red']}]")

        elapsed = time.time() - start_time
        console.print(f"\n  [{COLORS['dim']}]⏱ {elapsed:.1f}s[/{COLORS['dim']}]")
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
