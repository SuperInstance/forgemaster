"""Demo: run a 10-agent fleet with live dashboard."""

from metronome_dashboard.cli import main

if __name__ == "__main__":
    main(["watch", "-n", "10", "-r", "1.0"])
