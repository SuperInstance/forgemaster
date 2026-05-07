# python-agent-shell

Minimal interactive Python shell for SuperInstance fleet agents. PLATO integration, fleet-coordinate access, constraint theory tools — all through a REPL you can pipe into an agent's runtime.

## Install

```bash
git clone https://github.com/SuperInstance/python-agent-shell
cd python-agent-shell
pip install -r requirements.txt
```

## Quick Start

```bash
python3 src/shell.py [vessel-id]
```

Opens a REPL with fleet utilities pre-loaded. The `vessel-id` arg sets which agent context the shell runs under (auto-detects if omitted).

```python
# Inside the shell
>>> eval_insight("check drift on batch-42")
>>> help()   # Show available fleet commands
>>> history  # Show command history
```

## What's Working

- Core REPL with eval and help
- Command history
- Fleet utility imports

## What's Coming

- PLATO room read/write
- Fleet-coordinate import
- Constraint inference hooks

## Part of the SuperInstance Fleet

See [SuperInstance](https://github.com/SuperInstance) for the full fleet.
