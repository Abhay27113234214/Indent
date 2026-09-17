import os
import getpass
from rich.console import Console
from rich.theme import Theme
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

custom_theme = Theme({
    "info": "#bd93f9",
    "warning": "#f1fa8c",
    "error": "#ff5555",
})

console = Console(theme=custom_theme)

def get_rainbow_logo() -> Text:
    """Generates an unmistakable, completely solid >> with a true character-by-character rainbow gradient."""
    lines = [
        "██        ██",
        "████      ████",
        "██████    ██████",
        "████      ████",
        "██        ██"
    ]
    
    logo = Text()
    rainbow = [
        "#ff0000", "#ff3300", "#ff6600", "#ff9900", "#ffcc00", "#ffff00",
        "#ccff00", "#99ff00", "#66ff00", "#33ff00", "#00ff00", "#00ff66",
        "#00ffcc", "#00ffff", "#00ccff", "#0099ff"
    ]
    
    for line in lines:
        for i, char in enumerate(line):
            if char == "█":
                color = rainbow[min(i, len(rainbow)-1)]
                logo.append(char, style=f"bold {color}")
            else:
                logo.append(char)
        logo.append("\n")
        
    return logo

def print_welcome():
    grid = Table(show_header=False, box=None, padding=(0, 4))
    
    details = Table(show_header=False, box=None, padding=(0, 1))
    
    user_email = f"{getpass.getuser()}@indent.local"
    cwd = os.getcwd()
    
    details.add_row("[bold white]Indent Platform[/bold white]")
    details.add_row(f"[dim]User:[/dim] [green]{user_email}[/green]")
    details.add_row(f"[dim]Model:[/dim] [white]Gemini 3.1 Pro (High)[/white]")
    details.add_row(f"[dim]CWD:[/dim] [yellow]{cwd}[/yellow]")
    
    grid.add_row(get_rainbow_logo(), details)
    
    console.print(Panel(grid, border_style="dim cyan", padding=(0, 2)))
