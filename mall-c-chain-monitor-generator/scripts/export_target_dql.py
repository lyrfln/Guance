#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def safe_name(value):
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "_", value or "query").strip("_")
    return text[:120] or "query"


def iter_dql(checker, checker_idx, include_querylist=False):
    title = checker.get("jsonScript", {}).get("title", f"checker-{checker_idx}")
    for target_idx, target in enumerate(checker.get("jsonScript", {}).get("targets", []), start=1):
        dql = target.get("dql", "")
        if dql:
            yield f"{checker_idx:03d}_target_{target_idx}_{safe_name(title)}.dql", dql
    if include_querylist:
        for q_idx, item in enumerate(checker.get("extend", {}).get("querylist", []), start=1):
            query = item.get("query", {})
            q = query.get("q")
            if q:
                yield f"{checker_idx:03d}_querylist_{q_idx}_{safe_name(title)}.dql", q
            for child_idx, child in enumerate(query.get("children", []) or [], start=1):
                cq = child.get("q")
                if cq:
                    yield f"{checker_idx:03d}_querylist_{q_idx}_child_{child_idx}_{safe_name(title)}.dql", cq


def main():
    parser = argparse.ArgumentParser(description="Export DQL from generated Guance monitor JSON.")
    parser.add_argument("--input", required=True, help="Path to generated monitor JSON.")
    parser.add_argument("--out-dir", required=True, help="Directory to write .dql files.")
    parser.add_argument("--include-querylist", action="store_true", help="Also export extend.querylist query DQL and child DQL.")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for existing in out_dir.glob("*.dql"):
        existing.unlink()
    count = 0
    for checker_idx, checker in enumerate(data.get("checkers", []), start=1):
        for filename, dql in iter_dql(checker, checker_idx, args.include_querylist):
            (out_dir / filename).write_text(dql, encoding="utf-8")
            count += 1
    print(f"exported={count}")
    print(f"out_dir={out_dir}")


if __name__ == "__main__":
    main()
