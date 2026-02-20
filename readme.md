# terragenai

A minimal standalone CLI package inside this repository.

## Common Flags

```bash
python3 -m src.main --help
python3 -m src.main --version
python3 -m src.main --configure
```

`--configure` saves settings to your OS-specific user config directory.

## File Locations

- macOS:
  - Config: `~/Library/Application Support/TerragenAI/.terragenairc`
  - History: `~/Library/Application Support/TerragenAI/history.json`
- Windows:
  - Config: `%APPDATA%\\TerragenAI\\.terragenairc`
  - History: `%LOCALAPPDATA%\\TerragenAI\\history.json`
- Linux:
  - Config: `$XDG_CONFIG_HOME/terragenai/.terragenairc` (or `~/.config/terragenai/.terragenairc`)
  - History: `$XDG_STATE_HOME/terragenai/history.json` (or `~/.local/state/terragenai/history.json`)

Overrides:
- `TERRAGENAI_HOME` to place both files in a single custom directory.
- `TERRAGENAI_CONFIG_FILE` to set an exact config file path.
- `TERRAGENAI_HISTORY_FILE` to set an exact history file path.


## How to Install

```bash
pip install terragenai
terragenai
```
