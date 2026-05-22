.PHONY: run run-udp test clean

run:
	python3 run_demo.py

run-udp:
	python3 run_demo.py --udp --quick

test:
	python3 test_demo.py

clean:
	rm -rf __pycache__ agents/__pycache__ network/__pycache__
	rm -f demo/plato_tiles.db
