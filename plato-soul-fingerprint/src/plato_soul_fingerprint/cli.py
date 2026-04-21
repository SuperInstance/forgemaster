"""Command line interface for plato-soul-fingerprint."""

import argparse
import os
import sys
import json

from .extractor import SoulExtractor
from .analysis import soul_distance, soul_cluster, soul_report, soul_compare


def _find_soul_files(directory: str):
    souls = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".soul.json"):
                souls.append(os.path.join(root, f))
    return souls


def main():
    parser = argparse.ArgumentParser(
        prog="plato-soul-fingerprint",
        description="Extract soul vectors from git repositories.",
    )
    subparsers = parser.add_subparsers(dest="command")

    extract_parser = subparsers.add_parser("extract", help="Extract soul from a repo")
    extract_parser.add_argument("repo", help="Path to git repository")
    extract_parser.add_argument(
        "--output-dir", "-o", default=None, help="Directory to write .soul files"
    )
    extract_parser.add_argument(
        "--fit-repos", default=None, help="Comma-separated list of repos to fit PCA"
    )

    distance_parser = subparsers.add_parser("distance", help="Cosine distance between two repos")
    distance_parser.add_argument("repo_a", help="Path to first repo or .soul.json")
    distance_parser.add_argument("repo_b", help="Path to second repo or .soul.json")

    cluster_parser = subparsers.add_parser("cluster", help="Hierarchical cluster of repos")
    cluster_parser.add_argument("directory", help="Directory containing .soul.json files")

    report_parser = subparsers.add_parser("report", help="Human-readable soul report")
    report_parser.add_argument("repo", help="Path to repo or .soul.json")

    compare_parser = subparsers.add_parser("compare", help="Compare two repos")
    compare_parser.add_argument("repo_a", help="Path to first repo or .soul.json")
    compare_parser.add_argument("repo_b", help="Path to second repo or .soul.json")

    batch_parser = subparsers.add_parser("batch", help="Batch extract souls from a directory of repos")
    batch_parser.add_argument("directory", help="Directory containing git repos")
    batch_parser.add_argument("--output-dir", "-o", default=None, help="Output directory for soul files")

    sig_parser = subparsers.add_parser("signatures", help="Print soul signatures for all .soul.json files")
    sig_parser.add_argument("directory", help="Directory containing .soul.json files")

    args = parser.parse_args()

    if args.command == "extract":
        extractor = SoulExtractor()
        if args.fit_repos:
            fit_repos = [r.strip() for r in args.fit_repos.split(",")]
            extractor.fit(fit_repos)
            data = extractor.extract(args.repo)
            data = extractor.transform(data)
        else:
            data = extractor.extract(args.repo)
        json_path, txt_path = extractor.write(data, output_dir=args.output_dir)
        print(f"Wrote {json_path}")
        print(f"Wrote {txt_path}")

    elif args.command == "distance":
        a = args.repo_a
        b = args.repo_b
        if not a.endswith(".soul.json"):
            a = os.path.join(a, os.path.basename(a) + ".soul.json")
        if not b.endswith(".soul.json"):
            b = os.path.join(b, os.path.basename(b) + ".soul.json")
        d = soul_distance(a, b)
        print(f"Cosine distance: {d:.4f}")

    elif args.command == "cluster":
        souls = _find_soul_files(args.directory)
        if not souls:
            print("No .soul.json files found.", file=sys.stderr)
            sys.exit(1)
        result = soul_cluster(souls)
        print(f"Clustered {result['n_repos']} repositories")
        for i, name in enumerate(result["names"]):
            print(f"  [{i}] {name}")
        print("Linkage matrix (single linkage):")
        for row in result["linkage"]:
            print(f"  merge {int(row[0])} + {int(row[1])} -> dist={row[2]:.4f} size={int(row[3])}")

    elif args.command == "report":
        path = args.repo
        if not path.endswith(".soul.json"):
            path = os.path.join(path, os.path.basename(path) + ".soul.json")
        print(soul_report(path))

    elif args.command == "compare":
        a = args.repo_a
        b = args.repo_b
        if not a.endswith(".soul.json"):
            a = os.path.join(a, os.path.basename(a) + ".soul.json")
        if not b.endswith(".soul.json"):
            b = os.path.join(b, os.path.basename(b) + ".soul.json")
        print(soul_compare(a, b))

    elif args.command == "batch":
        from .analysis import batch_extract as _batch
        summary = _batch(args.directory, output_dir=args.output_dir)
        print(json.dumps(summary, indent=2))
        if summary.get("errors"):
            for e in summary["errors"]:
                print(f"  ERROR: {e['repo']} - {e['error']}", file=sys.stderr)

    elif args.command == "signatures":
        from .analysis import soul_signature
        souls = _find_soul_files(args.directory)
        if not souls:
            print("No .soul.json files found.", file=sys.stderr)
            sys.exit(1)
        for sf in souls:
            with open(sf, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(soul_signature(data))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
