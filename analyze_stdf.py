#!/usr/bin/env python3
"""CLI entry point for STDF file analysis."""

import sys

from stdf_analyzer.parser import parse_stdf_bz2
from stdf_analyzer.analyzer import analyze
from stdf_analyzer.formatter import print_report


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path-to-bz2-file>")
        sys.exit(1)

    bz2_path = sys.argv[1]
    print(f"Opening: {bz2_path}")

    parsed = parse_stdf_bz2(bz2_path)
    result = analyze(*parsed, file_path=bz2_path)
    print_report(result)


if __name__ == "__main__":
    main()
