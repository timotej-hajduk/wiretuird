# wiretuird

`wiretuird` is a small terminal UI for managing WireGuard configs stored in `/etc/wireguard`.
It gives you a simple list of available tunnels and lets you bring them up or down without opening a shell and typing `sudo` commands manually.

## Features

- Lists available `.conf` files from `/etc/wireguard`
- Shows which interfaces are currently active
- Brings an interface up or down with keyboard shortcuts or buttons
- Refreshes the list without restarting the app
- Works well for setups where `wg-quick` is allowed through passwordless `sudo`

## Requirements

- Linux
- WireGuard tools installed: `wg` and `wg-quick`
- Python 3.11 or newer
- Access to `/etc/wireguard`
- Passwordless `sudo` configured for the commands this app uses, unless you run the app as root

## Installation

### With `uv`

```bash
uv sync
uv run wiretuird
```

### With `pip`

```bash
pip install .
wiretuird
```

## Passwordless sudo setup

This app uses `sudo -n`, which means it will not prompt for a password.
If your system is not configured for passwordless sudo for the required commands, actions will fail.

Open the sudoers file safely:

```bash
sudo visudo
```

Add rules similar to these, adjusting the username if needed:

```sudoers
tim ALL=(root) NOPASSWD: /usr/bin/ls /etc/wireguard
tim ALL=(root) NOPASSWD: /usr/bin/wg-quick up *
tim ALL=(root) NOPASSWD: /usr/bin/wg-quick down *
```

You may also want to allow `wg show interfaces` if your system requires elevated access for it.
Use absolute command paths from your system, which you can check with:

```bash
command -v ls
command -v wg
command -v wg-quick
```

Review sudoers rules carefully before using them on a shared or sensitive machine.

## Usage

Launch the app:

```bash
wiretuird
```

The interface shows:

- `State`: whether a config is currently active
- `Config`: the `.conf` filename from `/etc/wireguard`
- `Interface`: the interface name derived from the filename

### Keybindings

- `u`: bring the selected interface up
- `d`: bring the selected interface down
- `r`: refresh the config list
- `q`: quit

You can also use the on-screen buttons.

## How it works

- Active interfaces are read with `wg show interfaces`
- Available configs are discovered in `/etc/wireguard`
- Up/down actions are executed with `wg-quick up <interface>` and `wg-quick down <interface>`
- Commands are run directly when the app is started as root, otherwise with `sudo -n`

## Limitations

- Built for Linux environments that use `/etc/wireguard`
- Assumes config filenames match interface names, for example `homevpn.conf` -> `homevpn`
- Currently focused on simple interface up/down management rather than detailed tunnel stats

## Development

Run the app locally:

```bash
uv run python -m wiretuird.main
```

## License

MIT. See [LICENSE](LICENSE).
