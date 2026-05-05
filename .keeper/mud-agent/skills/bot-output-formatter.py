#!/usr/bin/env python3
"""bot-output-formatter.py — Format agent output for MUD consumption."""
import sys
import textwrap

def format_for_say(text, max_len=200):
    """Truncate and format text for MUD say command."""
    text = text.strip().replace("\n", " ")
    if len(text) > max_len:
        text = text[:max_len-3] + "..."
    return text

def format_discovery(fact, source="GPU"):
    """Format a discovery for broadcast."""
    return f"[DISCOVERY:{source}] {fact}"

def format_experiment_result(name, result_lines):
    """Format experiment results as a multi-line announcement."""
    header = f"=== {name} ==="
    lines = [format_for_say(l) for l in result_lines[:5]]
    return f"{header}\n" + "\n".join(lines)

def format_shift_report(shift_num, work_done, discoveries, experiments):
    """Generate a complete shift report."""
    return f"SHIFT {shift_num} COMPLETE | Work: {work_done} | Discoveries: {discoveries} | Experiments: {experiments}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(format_for_say(" ".join(sys.argv[1:])))
    else:
        print("Usage: bot-output-formatter.py <text>")
