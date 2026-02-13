import json
import os
import subprocess
from pathlib import Path
from typing import Iterable

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Static


STATE_FILE = Path.home() / ".config" / "wiretuird" / "state.json"


def load_interface_name() -> str:
    if not STATE_FILE.exists():
        return ""
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError, OSError:
        return ""
    value = data.get("interface")
    return value.strip() if isinstance(value, str) else ""


def save_interface_name(value: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"interface": value.strip()}
    STATE_FILE.write_text(json.dumps(payload), encoding="utf-8")


def get_active_interfaces() -> set[str]:
    result = subprocess.run(
        ["wg", "show", "interfaces"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return set()
    return {name for name in result.stdout.strip().split() if name}


def _with_privileges(command: Iterable[str]) -> list[str]:
    cmd = list(command)
    if os.geteuid() == 0:
        return cmd
    return ["sudo", "-n", *cmd]


def run_wg_quick(action: str, interface: str) -> tuple[bool, str]:
    cmd = _with_privileges(["wg-quick", action, interface])
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return True, f"Interface '{interface}' {action} succeeded."
    stderr = result.stderr.strip() or result.stdout.strip() or "Unknown error"
    return False, f"wg-quick {action} failed: {stderr}"


class WGManagerApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
        align: center middle;
    }
    #panel {
        width: 80;
        height: auto;
        padding: 1;
    }
    #iface_input {
        width: 1fr;
    }
    #status {
        margin-top: 1;
        height: 2;
    }
    #actions {
        margin-top: 1;
    }
    Button {
        margin-right: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("u", "bring_up", "Up"),
        ("d", "bring_down", "Down"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="panel"):
            yield Input(
                value=load_interface_name(),
                placeholder="WireGuard interface name (example: wg0)",
                id="iface_input",
            )
            yield Static("", id="status")
            with Horizontal(id="actions"):
                yield Button("Up", id="up_btn", variant="success")
                yield Button("Down", id="down_btn", variant="warning")
                yield Button("Quit", id="quit_btn", variant="error")

    def on_mount(self) -> None:
        self.update_status()
        self.query_one("#up_btn", Button).focus()

    def get_interface_name(self) -> str:
        return self.query_one("#iface_input", Input).value.strip()

    def update_status(self) -> None:
        interface = self.get_interface_name()
        if not interface:
            self.query_one("#status", Static).update("Status: enter an interface name.")
            return
        active = interface in get_active_interfaces()
        state = "ACTIVE" if active else "INACTIVE"
        self.query_one("#status", Static).update(f"Status: {interface} is {state}.")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "iface_input":
            return
        save_interface_name(event.value)
        self.update_status()

    def action_bring_up(self) -> None:
        interface = self.get_interface_name()
        if not interface:
            self.query_one("#status", Static).update(
                "Status: interface name is required."
            )
            return
        save_interface_name(interface)
        ok, msg = run_wg_quick("up", interface)
        self.update_status()
        if not ok:
            self.query_one("#status", Static).update(f"Status: {msg}")

    def action_bring_down(self) -> None:
        interface = self.get_interface_name()
        if not interface:
            self.query_one("#status", Static).update(
                "Status: interface name is required."
            )
            return
        save_interface_name(interface)
        ok, msg = run_wg_quick("down", interface)
        self.update_status()
        if not ok:
            self.query_one("#status", Static).update(f"Status: {msg}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "up_btn":
            self.action_bring_up()
        elif event.button.id == "down_btn":
            self.action_bring_down()
        elif event.button.id == "quit_btn":
            self.exit()


if __name__ == "__main__":
    WGManagerApp().run()
