# stdf-analyzer

Python tool to parse and report on bz2-compressed STDF (Standard Test Data Format) V4 files from semiconductor testers.

## Setup

```sh
pip install -e .
```

Requires Python >=3.11. Key dependency: `pystdf` (pulls in numpy, openpyxl, pandas).

## CLI

```sh
stdf-analyzer path/to/file.std.bz2
# or
python analyze_stdf.py path/to/file.std.bz2
```

Input must be bz2-compressed STDF V4.

## Distribution

- `stdf-analyzer` — PyInstaller one-file binary (no source exposure). Run standalone anywhere, no Python or deps needed.
- `analyze_stdf_standalone.py` — single-file self-contained script (all modules inlined). Requires `pystdf` installed.

Build the binary:
```sh
pip install pyinstaller
pyinstaller --onefile --name stdf-analyzer analyze_stdf_standalone.py
```

## Package layout

- `analyze_stdf.py` — CLI entry point (also registered as `stdf-analyzer` console script)
- `analyze_stdf_standalone.py` — single-file version w/ all modules inlined, no local `.py` deps
- `stdf-analyzer` — pre-built PyInstaller binary (gitignored in `.gitignore`)
- `stdf_analyzer/` — library package
  - `models.py` — dataclasses (`MirData`, `MrrData`, `PcrData`, `SbrData`, `HbrData`, `AnalysisResult`)
  - `parser.py` — `pystdf`-based parser, filters to 7 record types only (Mir, Mrr, Pcr, Sbr, Hbr, Pir, Prr)
  - `analyzer.py` — constructs `AnalysisResult`, computes yield (bin1 / total parts)
  - `formatter.py` — prints human-readable report

## Conventions

- Type hints used throughout (Python 3.10+ union syntax `X | None`)
- No tests, no linter, no formatter, no type checker configured
- No CI
- `.bz2` and `.std` files are gitignored

## Gotchas

- `pystdf` uses a callback-driven parser (`Parser.addSink` with `after_send`); record fields are positional tuples decoded via `rec.fieldMap`
- Soft bin value `65535` means "no bin assigned"
- `HEAD_NUM == 255` is rendered as "ALL" in reports
- `PART_FLG` bit 0 = pass/fail, bit 4 = aborted
