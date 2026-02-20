# terragenai 

A minimal standalone CLI package inside this repository.

## Common Flags

```bash
python3 -m src.main --help
python3 -m src.main --version
python3 -m src.main --configure
```

`--configure` saves settings to your OS-specific user config directory.

Overrides:
- `TERRAGENAI_HOME` to place both files in a single custom directory.
- `TERRAGENAI_CONFIG_FILE` to set an exact config file path.
- `TERRAGENAI_HISTORY_FILE` to set an exact history file path.


## How to Install

```bash
pip install terragenai
terragenai
```
