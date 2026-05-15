# PlatoClaw Rooms

Loop Rooms — each one uses the fleet router to pick the right model automatically.

- `tic_tac_toe.py` — plays tic-tac-toe, routes moves through the router
- Officers maintain rooms, summarize activity, detect anomalies

Every room completion goes through POST /complete or lib/router.py.
Nobody thinks about which model powers which room.
