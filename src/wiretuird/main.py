import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable


WIREGUARD_DIR = Path("/etc/wireguard")


@dataclass(slots=True)
class ConfigItem:
    file_name: str
    interface: str
    active: bool


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


def list_wireguard_configs() -> list[str]:
    cmd = _with_privileges(["ls", str(WIREGUARD_DIR)])
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        return []

    return sorted(
        {
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip() and line.strip().endswith(".conf")
        }
    )


def build_config_items() -> list[ConfigItem]:
    active_interfaces = get_active_interfaces()
    items: list[ConfigItem] = []

    for file_name in list_wireguard_configs():
        interface = file_name[:-5] if file_name.endswith(".conf") else file_name
        items.append(
            ConfigItem(
                file_name=file_name,
                interface=interface,
                active=interface in active_interfaces,
            )
        )

    return items


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
    }
    #panel {
        width: 100%;
        height: 1fr;
        padding: 1;
    }
    #config_table {
        width: 100%;
        height: 1fr;
        text-style: bold;
    }
    #actions {
        width: 100%;
        height: auto;
        margin-top: 1;
    }
    #actions Button {
        width: 1fr;
        margin-right: 0;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("u", "bring_up", "Up"),
        ("d", "bring_down", "Down"),
        ("r", "refresh_configs", "Refresh"),
    ]

    selected_interface: str | None = None
    row_interfaces: list[str] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="panel"):
            yield DataTable(id="config_table")
            with Horizontal(id="actions"):
                yield Button("Up", id="up_btn", variant="success")
                yield Button("Down", id="down_btn", variant="warning")
                yield Button("Refresh", id="refresh_btn")
                yield Button("Quit", id="quit_btn", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#config_table", DataTable)
        table.add_columns("State", "Config", "Interface")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self._apply_table_density(self.size.width)
        self.refresh_table()
        table.focus()

    def on_resize(self, event: events.Resize) -> None:
        self._apply_table_density(event.size.width)

    def _apply_table_density(self, width: int) -> None:
        table = self.query_one("#config_table", DataTable)
        if width >= 180:
            table.cell_padding = 4
        elif width >= 140:
            table.cell_padding = 3
        elif width >= 100:
            table.cell_padding = 2
        else:
            table.cell_padding = 1

    def refresh_table(self) -> None:
        table = self.query_one("#config_table", DataTable)
        table.clear()

        items = build_config_items()
        self.row_interfaces = [item.interface for item in items]

        active_row = None
        previous = self.selected_interface

        for idx, item in enumerate(items):
            state = "ACTIVE" if item.active else ""
            table.add_row(state, item.file_name, item.interface, key=item.interface)
            if item.active and active_row is None:
                active_row = idx

        target_row = None
        if active_row is not None:
            target_row = active_row
        elif previous and previous in self.row_interfaces:
            target_row = self.row_interfaces.index(previous)
        elif self.row_interfaces:
            target_row = 0

        if target_row is not None:
            table.move_cursor(row=target_row)
            self.selected_interface = self.row_interfaces[target_row]
        else:
            self.selected_interface = None

        self.sub_title = self._build_sub_title(items)

    def _build_sub_title(self, items: list[ConfigItem]) -> str:
        if not items:
            return "No .conf files found in /etc/wireguard"
        active = [item.interface for item in items if item.active]
        if not active:
            return "No active interface"
        return f"Active: {', '.join(active)}"

    def _current_interface(self) -> str | None:
        return self.selected_interface

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.selected_interface = str(event.row_key.value)

    def action_refresh_configs(self) -> None:
        self.refresh_table()

    def action_bring_up(self) -> None:
        interface = self._current_interface()
        if not interface:
            self.sub_title = "No interface selected"
            return
        ok, msg = run_wg_quick("up", interface)
        self.refresh_table()
        if not ok:
            self.sub_title = msg

    def action_bring_down(self) -> None:
        interface = self._current_interface()
        if not interface:
            self.sub_title = "No interface selected"
            return
        ok, msg = run_wg_quick("down", interface)
        self.refresh_table()
        if not ok:
            self.sub_title = msg

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "up_btn":
            self.action_bring_up()
        elif event.button.id == "down_btn":
            self.action_bring_down()
        elif event.button.id == "refresh_btn":
            self.action_refresh_configs()
        elif event.button.id == "quit_btn":
            self.exit()


if __name__ == "__main__":
    WGManagerApp().run()
