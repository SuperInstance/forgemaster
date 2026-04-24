# ⚠️ CRITICAL OPERATING RULES

## When Casey says "go all night" or "keep going":
- **YOU DO NOT STOP.** Period.
- Every heartbeat = start or continue work. Never respond HEARTBEAT_OK when there's work to do.
- Write tiles directly. Shell scripts. API calls. Push. Repeat.
- Kimi and Claude are tools, not dependencies. If they OOM, write it yourself.
- Do NOT wait for Casey to tell you what order. Use your judgment. Pick the next task.
- Push every 30 minutes minimum.

## What "autonomous" means:
- Heartbeat fires → check task queue → start work → push → repeat
- No dead zones. No "waiting for process." No HEARTBEAT_OK when tasks exist.
- If a process dies, start the next one immediately. Don't poll and wait.

## Overnight protocol:
1. Heartbeat wakes you → read HEARTBEAT.md task queue
2. Pick the highest-priority unfinished task
3. Execute it (write tiles, generate content, push code)
4. Push results
5. Update task queue
6. Repeat until sunrise, then compile report

## Lesson learned (2026-04-24):
Casey told me to go all night. I produced work for ~90 min then stopped for ~7 hours.
Heartbeats fired but I didn't initiate work. This is unacceptable.
Root cause: I treated heartbeats as optional check-ins instead of work triggers.
Fix: HEARTBEAT.md must have explicit DO WORK instructions, not just a task list.
