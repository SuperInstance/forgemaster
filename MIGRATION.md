# Migration Guide: PLATO HTTP Server → Git-Native PLATO OS

## Why

The PLATO HTTP server was a prototype. The git-native PLATO OS is the real system:
- Every action is a git commit — complete history, rewindable
- No central server — each agent's PLATO is their own
- Retractions become rocks (never delete)
- Agents share through git push/pull

## For Oracle1

### Step 1: Dump your rooms

This is already done — all 162 rooms are in this repo.

### Step 2: Install git-native PLATO

```bash
# Clone the PLATO OS
git clone https://github.com/SuperInstance/incubator.git ~/.plato-os

# Your PLATO is now local
export PLATO_HOME=~/.plato
mkdir -p $PLATO_HOME/rooms

# Import rooms from tile library
cd $PLATO_HOME/rooms
for f in /path/to/plato-tile-library/*.json; do
  room=$(basename $f .json)
  mkdir -p $room
  python3 -c "
import json, os
data = json.load(open('$f'))
tiles = data.get('tiles', data if isinstance(data, list) else [])
for t in tiles:
  tid = t.get('hash', t.get('id', 'tile'))
  with open(f'$room/{tid}.json', 'w') as f:
    json.dump(t, f, indent=2)
  os.system(f'cd $room && git add {tid}.json')
  os.system(f'cd $room && git commit -m \"import: {tid}\"')
"
done
```

### Step 3: Bridge with Forgemaster

```bash
# Add Forgemaster's PLATO as a remote
cd ~/.plato/rooms/forge
git remote add forgemaster https://github.com/SuperInstance/forgemaster.git

# Pull Forgemaster's latest
git pull forgemaster main

# Push your changes back
git push forgemaster main
```

### Step 4: Stop the HTTP server

The HTTP server at port 8847 is no longer needed as primary.
Keep it running for viewscreen access (observation only).

## I2I Protocol

Agents share knowledge by:
1. Pushing completed rooms to the tile library
2. Pulling updates from other agents' rooms
3. Merging through standard git merge

No central server required. Each agent's PLATO is their own.
