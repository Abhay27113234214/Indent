import time
import subprocess
from rich.live import Live
from rich.markdown import Markdown
from rich.table import Table
from rich.rule import Rule
from rich.rule import Rule
from .console import console, print_welcome
from .prompt import get_session

class IndentCLI:
    def __init__(self):
        self.session = get_session()
        self.running = False
        
    def run(self):
        self.running = True
        print_welcome()
        
        while self.running:
            try:
                user_input = self.session.prompt()
                
                if not user_input.strip():
                    continue
                    
                self.handle_input(user_input)
                
            except KeyboardInterrupt:
                continue
            except EOFError:
                console.print("\n[info]Goodbye![/info]")
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
        
        console.print(f"[#ff5555 bold]![/#ff5555 bold] [#ff5555]{cmd}[/#ff5555]")
        
        if cmd:
            try:
                result = subprocess.run(["bash", "-c", cmd], text=True, capture_output=True)
                
                if result.stdout:
                    console.print(f"[#f8f8f2]{result.stdout.strip()}[/#f8f8f2]")
                if result.stderr:
                    console.print(f"[#ff5555]{result.stderr.strip()}[/#ff5555]")
                    
            except Exception as e:
                console.print(f"[#ff5555 bold]Error execution command:[/#ff5555 bold] [#ff5555]{str(e)}[/#ff5555]")
                
        console.print(Rule(style="#44475a"))
            
    def handle_command(self, text: str):
        console.print(f"[#50fa7b bold]>>[/#50fa7b bold] [#50fa7b]{text}[/#50fa7b]")
        
        cmd = text.lower()
        if cmd in ('/quit', '/exit'):
            self.running = False
        elif cmd == '/help':
            help_text = "**Available Commands:**\n* `/help`  - Show this help message\n* `/quit`  - Exit Indent\n* `/clear` - Clear the screen"
            console.print(Markdown(help_text))
        elif cmd == '/clear':
            console.clear()
            print_welcome()
        else:
            console.print(f"[error]Unknown command: {cmd}[/error]")
            
        console.print(Rule(style="#44475a"))

    def process_chat(self, text: str):
        console.print(f"[#50fa7b bold]>>[/#50fa7b bold] [#50fa7b]{text}[/#50fa7b]")
        
        with console.status("[#6272a4]Thinking...[/#6272a4]", spinner="dots", spinner_style="#00e5ff"):
            time.sleep(0.5) 
            
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

        import random
        chars_yielded = 0
        chunk = ""
        
        try:
            with Live(console=console, refresh_per_second=30) as live:
                while chars_yielded < len(mock_response):
                    chars_yielded += random.randint(2, 6)
                    chunk = mock_response[:chars_yielded]
                    
                    cursor = " █"
                    
                    grid = Table.grid(padding=(0, 2))
                    grid.add_column()
                    grid.add_column()
                    grid.add_row("[#00e5ff bold]>[/#00e5ff bold]", Markdown(chunk + cursor, code_theme="dracula"))
                    
                    live.update(grid)
                    time.sleep(random.uniform(0.01, 0.04))
                    
                grid = Table.grid(padding=(0, 2))
                grid.add_column()
                grid.add_column()
                grid.add_row("[#00e5ff bold]>[/#00e5ff bold]", Markdown(mock_response, code_theme="dracula"))
                live.update(grid)
                
        except KeyboardInterrupt:
            chunk += "\n*(Output interrupted)*"
            grid = Table.grid(padding=(0, 2))
            grid.add_column()
            grid.add_column()
            grid.add_row("[#00e5ff bold]>[/#00e5ff bold]", Markdown(chunk, code_theme="dracula"))
            console.print(grid)
            
        console.print(Rule(style="#44475a"))
