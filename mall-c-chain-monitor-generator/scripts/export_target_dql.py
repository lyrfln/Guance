#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Export target DQL from generated monitor JSON.")
    parser.add_argument("--input", required=True, help="Path to the generated monitor JSON.")
    parser.add_argument("--out-dir", required=True, help="Directory to write extracted .dql files.")
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    checkers = payload.get("checkers", [])

    for idx, checker in enumerate(checkers, start=1):
        title = checker.get("jsonScript", {}).get("title", f"checker-{idx}")
        safe_title = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in title)[:80]
        targets = checker.get("jsonScript", {}).get("targets", [])
        for target_idx, target in enumerate(targets, start=1):
            dql = target.get("dql", "")
            output = out_dir / f"{idx:03d}_{target_idx}_{safe_title}.dql"
            output.write_text(dql, encoding="utf-8")


if __name__ == "__main__":
    main()
