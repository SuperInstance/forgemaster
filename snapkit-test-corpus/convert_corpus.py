#!/usr/bin/env python3
"""Convert JSON corpus to binary format for Fortran validation."""
import struct
import json
import sys

def main():
    with open("corpus/snap_corpus.json") as f:
        corpus = json.load(f)

    with open("corpus/snap_corpus.bin", "wb") as f:
        for c in corpus:
            # Format: id(i32), x(f64), y(f64), a(i32), b(i32), snap_error(f64), snap_error_max(f64)
            f.write(struct.pack("<i", c["id"]))
            f.write(struct.pack("<d", c["input"]["x"]))
            f.write(struct.pack("<d", c["input"]["y"]))
            f.write(struct.pack("<i", c["expected"]["a"]))
            f.write(struct.pack("<i", c["expected"]["b"]))
            f.write(struct.pack("<d", c["snap_error"]))
            f.write(struct.pack("<d", c["snap_error_max"]))

    print(f"Converted {len(corpus)} cases to corpus/snap_corpus.bin")

if __name__ == "__main__":
    main()
