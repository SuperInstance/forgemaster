#!/usr/bin/env bash
# run_cluster.sh — Launch a 3-node distributed metronome cluster
# forgemaster:19840, oracle1:19841, kimi1:19842
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_SCRIPT="$SCRIPT_DIR/metronome_node.py"

echo "=== Distributed Metronome Cluster ==="
echo "Starting 3 nodes..."

# Cleanup any previous runs
pkill -f "metronome_node.py" 2>/dev/null || true
sleep 1

# Launch 3 nodes
python3 "$NODE_SCRIPT" --name forgemaster --port 19840 --ticks 10000 --delta 0.0001 &
PID1=$!
python3 "$NODE_SCRIPT" --name oracle1 --port 19840 --ticks 10000 --delta 0.0001 &
PID2=$!
python3 "$NODE_SCRIPT" --name kimi1 --port 19840 --ticks 10000 --delta 0.0001 &
PID3=$!

echo "Launched: forgemaster (PID $PID1), oracle1 (PID $PID2), kimi1 (PID $PID3)"

# Status function
check_status() {
    echo ""
    echo "--- Fleet Status ($(date +%H:%M:%S)) ---"
    for pid in $PID1 $PID2 $PID3; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "  PID $pid: RUNNING"
        else
            echo "  PID $pid: STOPPED"
        fi
    done
}

# Phase 1: Run 60 seconds with status every 10
echo ""
echo "=== Phase 1: Running 60 seconds ==="
for i in $(seq 1 6); do
    sleep 10
    check_status
done

# Phase 2: Sunset node 1 (forgemaster)
echo ""
echo "=== Phase 2: Sunsetting forgemaster (SIGTERM to PID $PID1) ==="
kill -TERM "$PID1" 2>/dev/null || true
sleep 2
check_status

# Phase 3: Run 30 more seconds
echo ""
echo "=== Phase 3: Running 30 more seconds ==="
for i in $(seq 1 3); do
    sleep 10
    check_status
done

# Final status
echo ""
echo "=== Final Status ==="
check_status

# Cleanup
echo ""
echo "Cleaning up..."
kill "$PID2" "$PID3" 2>/dev/null || true
wait "$PID1" 2>/dev/null || true
wait "$PID2" 2>/dev/null || true
wait "$PID3" 2>/dev/null || true

echo "=== Cluster run complete ==="
