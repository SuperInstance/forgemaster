#!/usr/bin/env python3
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

URL = "http://147.224.38.131:8847"

def audit_room(name):
    try:
        tiles = requests.get(f"{URL}/room/{name}", timeout=15).json().get("tiles", [])
    except Exception:
        return None
    answers = set()
    checks = [0, 0, 0, 0, 0]
    for t in tiles:
        q = t.get("question", "")
        a = t.get("answer", "")
        c = [
            len(q) >= 20,
            "?" in q,
            bool(t.get("domain")),
            a not in answers,
            0 <= t.get("score", -1) <= 5,
        ]
        answers.add(a)
        for i, ok in enumerate(c):
            checks[i] += ok
    n = len(tiles) or 1
    return (name, len(tiles), *[round(c / n * 100, 1) for c in checks])

def main():
    rooms = requests.get(f"{URL}/rooms", timeout=15).json()
    results = []
    with ThreadPoolExecutor(max_workers=32) as ex:
        futs = {ex.submit(audit_room, n): n for n in rooms}
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                results.append(res)
    results.sort(key=lambda x: sum(x[2:]), reverse=True)
    hdr = "| Room | Tiles | Len | ? | Domain | Unique | Score | Quality |"
    sep = "|------|-------|-----|---|--------|--------|-------|---------|"
    print(hdr)
    print(sep)
    for r in results:
        q = round(sum(r[2:]) / 5, 1)
        print(f"| {r[0]} | {r[1]} | {r[2]}% | {r[3]}% | {r[4]}% | {r[5]}% | {r[6]}% | {q}% |")

if __name__ == "__main__":
    main()
