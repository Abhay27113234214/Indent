import os
import time
import random
import getpass
import shutil
from datetime import datetime
from rich.console import Console
from rich.theme import Theme
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

COLORS = {
    "cyan":     "#00e5ff",
    "purple":   "#bd93f9",
    "green":    "#50fa7b",
    "yellow":   "#f1fa8c",
    "red":      "#ff5555",
    "orange":   "#ffb86c",
    "pink":     "#ff79c6",
    "white":    "#f8f8f2",
    "dim":      "#6272a4",
    "bg_dark":  "#282a36",
    "bg_line":  "#44475a",
    "shadow":   "#333645",
}

custom_theme = Theme({
    "info":    COLORS["purple"],
    "warning": COLORS["yellow"],
    "error":   COLORS["red"],
})

console = Console(theme=custom_theme)

RAINBOW = [
    "#ff0055", "#ff0033", "#ff1100", "#ff3300", "#ff5500", "#ff7700",
    "#ff9900", "#ffbb00", "#ffdd00", "#eeff00", "#ccff00", "#99ff00",
    "#66ff00", "#33ff00", "#00ff22", "#00ff55", "#00ff88", "#00ffbb",
    "#00ffdd", "#00ffff", "#00ddff", "#00bbff", "#0099ff", "#0077ff",
    "#0055ff", "#0033ff", "#1100ff", "#3300ff", "#5500ff", "#7700ff",
]

_FONT = {
    'I': ["██", "██", "██", "██", "██"],
    'N': ["██    ██", "████  ██", "██ ██ ██", "██  ████", "██    ██"],
    'D': ["██████  ", "██   ██ ", "██    ██", "██   ██ ", "██████  "],
    'E': ["████████", "██      ", "██████  ", "██      ", "████████"],
    'T': ["████████", "   ██   ", "   ██   ", "   ██   ", "   ██   "],
}

def _build_title(word: str, gap: str = "  ") -> list:
    """Build a large block title by joining letter definitions side by side."""
    return [gap.join(_FONT[ch][row] for ch in word) for row in range(5)]

TITLE_LINES = _build_title("INDENT")

LOGO_LINES = [
    "██            ██",
    "  ████          ████",
    "    ██████        ██████",
    "      ████████      ████████",
    "        ██████████    ██████████",
    "      ████████      ████████",
    "    ██████        ██████",
    "  ████          ████",
    "██            ██",
]

TIPS = [
    "Type [bold]![/bold] followed by a command to run bash directly",
    "Press [bold]Alt+Enter[/bold] to write multiline prompts",
    "Use [bold]/clear[/bold] to reset the screen",
    "Code blocks are syntax-highlighted with the Dracula theme",
    "Use [bold]/help[/bold] to see all available commands",
]

def _add_shadow(lines: list[str], dx: int = 1, dy: int = 1) -> list[str]:
    """
    Given a list of strings representing ASCII art, returns a new list of strings
    where a shadow (represented by 'S') is drawn at an offset of (dx, dy).
    """
    height = len(lines)
    if height == 0:
        return []
    
    width = max(len(line) for line in lines)
    canvas_height = height + dy
    canvas_width = width + dx

    canvas = [[" " for _ in range(canvas_width)] for _ in range(canvas_height)]

    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if char != " ":
                canvas[y + dy][x + dx] = "S"

    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if char != " ":
                canvas[y][x] = char

    return ["".join(row).rstrip() for row in canvas]

def _apply_rainbow(lines: list[str]) -> Text:
    """Applies the horizontal rainbow gradient to a list of ASCII strings."""
    text = Text(no_wrap=True)
    for line in lines:
        for i, char in enumerate(line):
            if char == "█":
                text.append("█", style=f"bold {RAINBOW[min(i, len(RAINBOW) - 1)]}")
            elif char == "S":
                text.append("█", style=COLORS["shadow"])
            else:
                text.append(char)
        text.append("\n")
    return text

class OutlineShadowBox:
    """A custom renderable that wraps another renderable with an outline-style drop shadow (like claude-code)."""
    def __init__(self, renderable):
        self.renderable = renderable

    def __rich_measure__(self, console, options):
        from rich.measure import Measurement
        measurement = Measurement.get(console, options, self.renderable)
        return Measurement(measurement.maximum + 1, measurement.maximum + 1)

    def __rich_console__(self, console, options):
        from rich.measure import Measurement
        from rich.segment import Segment
        from rich.style import Style
        
        measurement = Measurement.get(console, options, self.renderable)
        width = measurement.maximum
        
        lines = console.render_lines(self.renderable, options.update(width=width))
        shadow_style = Style(color=COLORS["dim"])
        
        for i, line in enumerate(lines):
            if i == 0:
                yield from line
                yield Segment("\n")
            elif i == 1:
                yield from line
                yield Segment("╮", shadow_style)
                yield Segment("\n")
            else:
                yield from line
                yield Segment("│", shadow_style)
                yield Segment("\n")
                
        if lines:
            yield Segment(" ╰", shadow_style)
            yield Segment("─" * (width - 2), shadow_style)
            yield Segment("╯\n", shadow_style)

def print_welcome():
    """
    Animated startup sequence:
    1. The shadowed INDENT title sweeps in line by line alongside the logo and details
    2. The full banner appears with a subtitle
    3. A random tip is shown below
    """
    shadowed_title_lines = _add_shadow(TITLE_LINES)
    shadowed_logo_lines = _add_shadow(LOGO_LINES)

    logo = _apply_rainbow(shadowed_logo_lines)
    
    from rich import box
    details_inner = Table(show_header=False, box=None, padding=(0, 1))
    user_name = getpass.getuser()
    cwd = os.getcwd()
    now = datetime.now().strftime("%b %d, %Y  %H:%M")

    details_inner.add_row(f"[{COLORS['dim']}]  ●  User  [/{COLORS['dim']}] [{COLORS['green']}]{user_name}[/{COLORS['green']}]")
    details_inner.add_row(f"[{COLORS['dim']}]  ●  Model [/{COLORS['dim']}] [{COLORS['purple']}]Gemini 3.1 Pro[/{COLORS['purple']}]")
    details_inner.add_row(f"[{COLORS['dim']}]  ●  Path  [/{COLORS['dim']}] [{COLORS['yellow']}]{cwd}[/{COLORS['yellow']}]")
    details_inner.add_row(f"[{COLORS['dim']}]  ●  Time  [/{COLORS['dim']}] [{COLORS['orange']}]{now}[/{COLORS['orange']}]")

    details_box = Table(show_header=False, box=box.ROUNDED, border_style=COLORS["dim"], padding=(0, 1))
    details_box.add_row(details_inner)
    
    details = OutlineShadowBox(details_box)

    with Live(console=console, refresh_per_second=20) as live:
        building_title = Text(no_wrap=True)

        for line in shadowed_title_lines:
            for i, char in enumerate(line):
                if char == "█":
                    color = RAINBOW[min(i, len(RAINBOW) - 1)]
                    building_title.append(char, style=f"bold {color}")
                elif char == "S":
                    building_title.append("█", style=COLORS["shadow"])
                else:
                    building_title.append(char)
            building_title.append("\n")

            main_grid = Table(show_header=False, box=None, padding=(0, 2), expand=False)
            main_grid.add_column(justify="left", vertical="middle")
            main_grid.add_column(justify="left", vertical="middle")
            main_grid.add_column(justify="left", vertical="middle")
            main_grid.add_row(logo, building_title, details)

            live.update(Panel(
                main_grid,
                border_style=COLORS["dim"],
                padding=(1, 2),
            ))
            time.sleep(0.07)

        time.sleep(0.2)

        final_grid = Table(show_header=False, box=None, padding=(0, 2), expand=False)
        final_grid.add_column(justify="left", vertical="middle")
        final_grid.add_column(justify="left", vertical="middle")
        final_grid.add_column(justify="left", vertical="middle")
        final_grid.add_row(logo, building_title, details)

        live.update(Panel(
            final_grid,
            border_style=COLORS["dim"],
            padding=(1, 2),
            subtitle=f"[{COLORS['dim']}]v0.1.0 — Type /help for commands[/{COLORS['dim']}]",
            subtitle_align="right",
        ))

    tip = random.choice(TIPS)
    console.print(f"  [{COLORS['dim']}]💡 {tip}[/{COLORS['dim']}]")
    console.print()

def print_goodbye():
    """Print a styled goodbye message on exit."""
    console.print()
    goodbye = Text()
    msg = "━━━━  See you next time!  ━━━━"
    for char in msg:
        if char == "━":
            goodbye.append(char, style=COLORS["dim"])
        elif char == " ":
            goodbye.append(char)
        else:
            goodbye.append(char, style=f"bold {COLORS['white']}")
    console.print(f"  ", end="")
    console.print(goodbye)
    console.print()
