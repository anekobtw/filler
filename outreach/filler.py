"""Keyboard-first terminal interface for Resume Filler."""

from __future__ import annotations
import curses
import json
import secrets
import shutil
import subprocess
import textwrap
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .associations import SearchResult, linkedin_candidates
from .config import applicant_details, load_config
from .firefox import open_firefox
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_NAME = "resume.config.json"



@dataclass(frozen=True)
class MenuItem:
    label: str
    detail: str
    action: str


MENU_ITEMS = (
    MenuItem("Build and load into Firefox", "Build the extension and open Firefox's temporary add-on page.", "build"),
    MenuItem("Change your info", "Edit the answers bundled into the extension.", "info"),
    MenuItem("Autofill the open page", "Ask Firefox to fill the page active when this action starts.", "autofill"),
    MenuItem("Search top 10 company connections", "Find and browse up to ten LinkedIn connections.", "search"),
)


def build_extension(root: Path = PROJECT_ROOT) -> str:
    """Build the extension, then take the user to Firefox's required load screen."""
    result = subprocess.run(
        ["npm", "run", "build"], cwd=root, text=True, capture_output=True, check=False
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        return f"Build failed: {detail or 'npm run build exited unsuccessfully.'}"

    firefox = shutil.which("firefox")
    if firefox is None:
        return "Build completed, but Firefox was not found on PATH."
    subprocess.Popen(
        [firefox, "--new-tab", "about:debugging#/runtime/this-firefox"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return "Build complete. In Firefox: Load Temporary Add-on → dist/manifest.json."


def save_config(config: dict[str, object], path: Path | None = None) -> None:
    (path or Path.cwd() / CONFIG_NAME).write_text(
        json.dumps(config, indent=2) + "\n",
        encoding="utf-8",
    )



def request_autofill(timeout: float = 10) -> str:
    """Authorize one extension request, then fill Firefox's previously active tab."""
    token = secrets.token_urlsafe(32)
    path = f"/autofill/{token}"
    requested = False

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            nonlocal requested
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}" or self.path != path:
                self.send_error(404)
                return
            body = json.dumps({"type": "autofill", "token": token}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            requested = True

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        server.timeout = 0.25
        deadline = time.monotonic() + timeout
        while not requested and time.monotonic() < deadline:
            server.handle_request()
    return "Autofill requested." if requested else "Extension did not respond. Reload it in Firefox and retry."
class FillerApp:
    """Curses views and action orchestration; no terminal setup occurs at import time."""

    primary = 1
    selected = 2
    muted = 3
    error = 4

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or Path.cwd() / CONFIG_NAME

    def run(self) -> None:
        curses.wrapper(self._main)

    def _main(self, screen: curses.window) -> None:
        curses.curs_set(0)
        screen.keypad(True)
        self._configure_colors()
        selected = 0
        while True:
            self._draw_menu(screen, selected)
            key = screen.getch()
            if key in (ord("q"), 27):
                return
            if key in (curses.KEY_UP, ord("k")):
                selected = (selected - 1) % len(MENU_ITEMS)
            elif key in (curses.KEY_DOWN, ord("j")):
                selected = (selected + 1) % len(MENU_ITEMS)
            elif key in (curses.KEY_ENTER, 10, 13):
                self._choose(screen, MENU_ITEMS[selected].action)

    def _configure_colors(self) -> None:
        if not curses.has_colors():
            return
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(self.primary, curses.COLOR_BLUE, -1)
        curses.init_pair(self.selected, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(self.muted, curses.COLOR_CYAN, -1)
        curses.init_pair(self.error, curses.COLOR_RED, -1)

    def _draw_menu(self, screen: curses.window, selected: int) -> None:
        screen.erase()
        height, width = screen.getmaxyx()
        title = " filler "
        screen.addnstr(1, max(2, (width - len(title)) // 2), title, width - 4, curses.color_pair(self.primary) | curses.A_BOLD)
        screen.addnstr(3, 4, "Resume Filler command center", width - 8, curses.A_BOLD)
        for index, item in enumerate(MENU_ITEMS):
            y = 5 + index * 3
            style = curses.color_pair(self.selected) | curses.A_BOLD if index == selected else curses.color_pair(self.primary)
            marker = "›" if index == selected else " "
            screen.addnstr(y, 4, f"{marker} {index + 1}. {item.label}", width - 8, style)
            screen.addnstr(y + 1, 8, item.detail, width - 12, curses.color_pair(self.muted))
        for offset, line in enumerate(textwrap.wrap(self.status, max(20, width - 8))[:2]):
            screen.addnstr(height - 4 + offset, 4, line, width - 8, curses.color_pair(self.muted))
        screen.addnstr(height - 1, 4, "↑/↓ navigate  Enter select  q quit", width - 8, curses.A_DIM)
        screen.refresh()

    def _choose(self, screen: curses.window, action: str) -> None:
        if action == "build":
            self._run_build(screen)
        elif action == "info":
            self._edit_info(screen)
        elif action == "autofill":
            self._autofill_instructions(screen)
        else:
            self._search_connections(screen)

    def _run_build(self, screen: curses.window) -> None:
        self.status = "Building extension…"
        screen.erase()
        screen.addstr(2, 4, self.status, curses.color_pair(self.primary) | curses.A_BOLD)
        screen.refresh()
        curses.def_prog_mode()
        curses.endwin()
        self.status = build_extension(PROJECT_ROOT)
        curses.reset_prog_mode()
        screen.refresh()

    def _prompt(self, screen: curses.window, prompt: str, initial: str = "") -> str | None:
        height, width = screen.getmaxyx()
        screen.move(height - 3, 0)
        screen.clrtoeol()
        screen.addnstr(height - 3, 4, prompt, width - 8, curses.color_pair(self.primary) | curses.A_BOLD)
        screen.addnstr(height - 2, 4, initial, width - 8)
        screen.move(height - 2, min(width - 5, 4 + len(initial)))
        curses.curs_set(1)
        curses.echo()
        try:
            value = screen.getstr(height - 2, 4, width - 8).decode().strip()
        except KeyboardInterrupt:
            return None
        finally:
            curses.noecho()
            curses.curs_set(0)
        return value

    def _edit_info(self, screen: curses.window) -> None:
        try:
            config = load_config(self.config_path)
            fields = config["fields"]
            if not isinstance(fields, list):
                raise ValueError("fields must be a list")
        except (OSError, ValueError, json.JSONDecodeError, KeyError) as error:
            self.status = f"Could not read resume.config.json: {error}"
            return

        selected = 0
        while True:
            screen.erase()
            height, width = screen.getmaxyx()
            screen.addnstr(1, 4, "Change your info", width - 8, curses.color_pair(self.primary) | curses.A_BOLD)
            screen.addnstr(2, 4, "↑/↓ choose  Enter edit  s save  Esc return", width - 8, curses.color_pair(self.muted))
            visible = max(1, height - 7)
            first = min(max(0, selected - visible + 1), max(0, len(fields) - visible))
            for row, field in enumerate(fields[first:first + visible], start=4):
                if not isinstance(field, dict):
                    continue
                index = first + row - 4
                keywords = field.get("keywords", [])
                label = str(keywords[0]).replace("_", " ").title() if keywords else f"Field {index + 1}"
                value = str(field.get("value", ""))
                style = curses.color_pair(self.selected) if index == selected else 0
                screen.addnstr(row, 4, f"{'›' if index == selected else ' '} {label}: {value}", width - 8, style)
            screen.refresh()
            key = screen.getch()
            if key in (27, ord("q")):
                return
            if key in (curses.KEY_UP, ord("k")):
                selected = (selected - 1) % len(fields)
            elif key in (curses.KEY_DOWN, ord("j")):
                selected = (selected + 1) % len(fields)
            elif key in (10, 13, curses.KEY_ENTER):
                field = fields[selected]
                if isinstance(field, dict):
                    value = self._prompt(screen, "New value (blank clears):", str(field.get("value", "")))
                    if value is not None:
                        field["value"] = value
            elif key == ord("s"):
                save_config(config, self.config_path)
                self.status = "Saved. Select Build and load into Firefox to bundle the updated answers."
                return

    def _autofill_instructions(self, screen: curses.window) -> None:
        screen.erase()
        screen.addstr(2, 4, "Requesting autofill from Firefox…", curses.color_pair(self.primary) | curses.A_BOLD)
        screen.refresh()
        curses.def_prog_mode()
        curses.endwin()
        self.status = request_autofill()
        curses.reset_prog_mode()
        screen.refresh()

    def _search_connections(self, screen: curses.window) -> None:
        company = self._prompt(screen, "Company to search:")
        if not company:
            self.status = "A company name is required."
            return
        try:
            _, associations = applicant_details(self.config_path)
            screen.erase()
            screen.addstr(2, 4, "Searching LinkedIn through Firefox…", curses.color_pair(self.primary) | curses.A_BOLD)
            screen.refresh()
            candidates = linkedin_candidates(company, associations, show_progress=False)[:10]
        except (OSError, ValueError, RuntimeError) as error:
            self.status = str(error)
            return
        self._show_connections(screen, company, candidates)
        self.status = f"Displayed {len(candidates)} connection(s) for {company}."

    def _show_connections(self, screen: curses.window, company: str, candidates: list[tuple[SearchResult, list[str]]]) -> None:
        if not candidates:
            self._message(screen, f"Top connections for {company}", ["No matches returned by LinkedIn."])
            return
        selected = 0
        while True:
            candidate, matches = candidates[selected]
            screen.erase()
            height, width = screen.getmaxyx()
            screen.addnstr(2, 4, f"{company} — connection {selected + 1} of {len(candidates)}", width - 8, curses.color_pair(self.primary) | curses.A_BOLD)
            details = (
                (f"{selected + 1}. {candidate.name}", curses.A_BOLD),
                (candidate.url, curses.color_pair(self.muted)),
                (f"Connection: {', '.join(matches)}", 0),
                (candidate.snippet or "No LinkedIn profile summary returned.", 0),
            )
            row = 4
            for text, style in details:
                for wrapped in textwrap.wrap(text, max(20, width - 8)) or [""]:
                    screen.addnstr(row, 4, wrapped, width - 8, style)
                    row += 1
                row += 1
            screen.addnstr(height - 2, 4, "←/→ previous/next  Enter or Esc return", width - 8, curses.color_pair(self.muted))
            screen.refresh()
            key = screen.getch()
            if key in (10, 13, curses.KEY_ENTER, 27, ord("q")):
                return
            if key in (curses.KEY_LEFT, ord("h")):
                selected = (selected - 1) % len(candidates)
            elif key in (curses.KEY_RIGHT, ord("l")):
                selected = (selected + 1) % len(candidates)

    def _message(self, screen: curses.window, title: str, lines: list[str]) -> None:
        screen.erase()
        height, width = screen.getmaxyx()
        screen.addnstr(2, 4, title, width - 8, curses.color_pair(self.primary) | curses.A_BOLD)
        row = 4
        for line in lines:
            for wrapped in textwrap.wrap(line, max(20, width - 8)) or [""]:
                if row >= height - 2:
                    break
                screen.addnstr(row, 4, wrapped, width - 8)
                row += 1
            row += 1
        screen.addnstr(height - 2, 4, "Press any key to return", width - 8, curses.color_pair(self.muted))
        screen.refresh()
        screen.getch()


def main() -> None:
    FillerApp().run()


if __name__ == "__main__":
    main()
