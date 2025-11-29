#!/usr/bin/env python3
"""Quick diagnostic for SimplifiedSpellChecker._apply_paradigm_rule().

Usage (from repo root):
    python tools/diagnose_paradigms.py            # default: 10 random roots
    python tools/diagnose_paradigms.py 25         # custom sample size
"""

from __future__ import annotations

import os
import random
import re
import sys
from collections import defaultdict
from typing import DefaultDict, Dict, List, Sequence, Tuple

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
PARADIGM_DIR = os.path.join(REPO_ROOT, os.pardir, "paradigms", "all")

HEADER_RE = re.compile(r"(?P<root>[A-Za-z]+)\((?P<tag>[A-Z]+\d*)\)")
FILENAME_RE = re.compile(r"^(?P<root>.*?)(?P<tag>[A-Z]+\d*)$")

# Ensure the repository root is on sys.path before importing project modules.
sys.path.append(os.path.abspath(os.path.join(REPO_ROOT, os.pardir)))
from enhanced_spell_checker import SimplifiedSpellChecker  # type: ignore # noqa: E402


def infer_root(file_name: str, rule: str) -> str:
    """Infer a paradigm root using the same heuristics as the spell checker."""
    header_match = HEADER_RE.search(rule)
    if header_match:
        return header_match.group("root")

    stem = file_name.split("_", 1)[0]
    file_match = FILENAME_RE.match(stem)
    if file_match:
        return file_match.group("root")

    return stem


def collect_paradigm_records() -> Dict[str, List[Tuple[str, str, str, int]]]:
    """Collect paradigm entries grouped by inferred root."""
    records: DefaultDict[str, List[Tuple[str, str, str, int]]] = defaultdict(list)

    if not os.path.isdir(PARADIGM_DIR):
        raise FileNotFoundError(f"Paradigm directory not found: {PARADIGM_DIR}")

    for file_name in sorted(os.listdir(PARADIGM_DIR)):
        if not file_name.endswith(".txt"):
            continue

        full_path = os.path.join(PARADIGM_DIR, file_name)
        with open(full_path, "r", encoding="utf-8") as handle:
            for line_no, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split(maxsplit=1)
                if len(parts) < 2:
                    continue

                surface, rule = parts
                root = infer_root(file_name, rule)
                records[root].append((surface, rule, file_name, line_no))

    return records


def run_diagnostic(sample_size: int = 10, per_root_limit: int = 10) -> None:
    rng = random.Random(42)  # deterministic sampling
    records_by_root = collect_paradigm_records()

    all_roots: List[str] = [root for root, entries in records_by_root.items() if entries]
    if not all_roots:
        print("No paradigm entries found.")
        return

    chosen_roots: Sequence[str] = rng.sample(all_roots, min(sample_size, len(all_roots)))
    matcher = SimplifiedSpellChecker._apply_paradigm_rule

    mismatches: List[Tuple[str, str, str, str, str, int]] = []
    totals = {"checked": 0, "matched": 0}

    for root in chosen_roots:
        entries = records_by_root[root]
        rng.shuffle(entries)
        subset = entries[:per_root_limit]

        print(f"\n=== Root: {root} ({len(entries)} entries, showing {len(subset)}) ===")
        for surface, rule, file_name, line_no in subset:
            totals["checked"] += 1
            generated = matcher(root, root, rule)
            if generated == surface:
                totals["matched"] += 1
                print(f"  ✓ {surface}")
            else:
                mismatches.append((root, surface, generated, rule, file_name, line_no))
                print(f"  ✗ expected {surface} → got {generated}")

    print("\n=== Summary ===")
    print(f"Total forms checked : {totals['checked']}")
    print(f"Exact matches       : {totals['matched']}")
    print(f"Mismatches          : {len(mismatches)}")

    if mismatches:
        print("\n--- Detailed mismatches ---")
        for root, expected, got, rule, file_name, line_no in mismatches:
            print(
                f"[{file_name}:{line_no}] root={root}\n"
                f"  rule     = {rule}\n"
                f"  expected = {expected}\n"
                f"  got      = {got}\n"
            )


if __name__ == "__main__":
    sample = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    run_diagnostic(sample_size=sample)
