#!/usr/bin/env python3
"""Standalone STDF analyzer — single file, no local dependencies."""

from __future__ import annotations

import bz2
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from pystdf import V4
from pystdf.IO import Parser


# ── models ──────────────────────────────────────────────────────────────────

@dataclass
class MirData:
    lot_id: str
    part_type: str
    job_name: str
    job_rev: Optional[str]
    tester_type: str
    node_name: str
    operator_name: str
    test_temp: Optional[float]
    facility_id: Optional[str]
    floor_id: Optional[str]
    exec_type: Optional[str]
    user_text: Optional[str]
    start_t: Optional[float]
    setup_t: Optional[float]


@dataclass
class MrrData:
    finish_t: Optional[float]


@dataclass
class PcrData:
    head_num: Optional[int]
    site_num: Optional[int]
    part_cnt: int
    good_cnt: int
    func_cnt: int
    abort_cnt: int
    retest_cnt: int


@dataclass
class SbrData:
    head_num: Optional[int]
    site_num: int
    sbin_num: int
    sbin_cnt: int
    sbin_pf: Optional[int]
    sbin_nam: Optional[str]


@dataclass
class HbrData:
    head_num: Optional[int]
    site_num: int
    hbin_num: int
    hbin_cnt: int
    hbin_pf: Optional[int]
    hbin_nam: Optional[str]


@dataclass
class AnalysisResult:
    mir: Optional[MirData]
    mrr: Optional[MrrData]
    pcr_list: list[PcrData]
    sbr_list: list[SbrData]
    hbr_list: list[HbrData]
    pir_count: int
    prr_pass: int
    prr_fail: int
    prr_aborted: int
    soft_bins: dict[int, int]
    no_bin: int
    file_path: str = ""


# ── parser ──────────────────────────────────────────────────────────────────

NEEDED_TYPES = [r for r in V4.records if r.__class__ in (
    V4.Mir, V4.Mrr, V4.Pcr, V4.Sbr, V4.Hbr, V4.Pir, V4.Prr)]


def _to_dict(rec, fields):
    return {k: v for (k, _), v in zip(rec.fieldMap, fields)}


def _build_mir(raw: dict) -> MirData:
    return MirData(
        lot_id=raw.get("LOT_ID", ""),
        part_type=raw.get("PART_TYP", ""),
        job_name=raw.get("JOB_NAM", ""),
        job_rev=raw.get("JOB_REV"),
        tester_type=raw.get("TSTR_TYP", ""),
        node_name=raw.get("NODE_NAM", ""),
        operator_name=raw.get("OPER_NAM", ""),
        test_temp=raw.get("TST_TEMP"),
        facility_id=raw.get("FACIL_ID"),
        floor_id=raw.get("FLOOR_ID"),
        exec_type=raw.get("EXEC_TYP"),
        user_text=raw.get("USER_TXT"),
        start_t=raw.get("START_T"),
        setup_t=raw.get("SETUP_T"),
    )


def _build_mrr(raw: dict) -> MrrData:
    return MrrData(finish_t=raw.get("FINISH_T"))


def _build_pcr(raw: dict) -> PcrData:
    return PcrData(
        head_num=raw.get("HEAD_NUM"),
        site_num=raw.get("SITE_NUM"),
        part_cnt=raw.get("PART_CNT") or 0,
        good_cnt=raw.get("GOOD_CNT") or 0,
        func_cnt=raw.get("FUNC_CNT") or 0,
        abort_cnt=raw.get("ABRT_CNT") or 0,
        retest_cnt=raw.get("RTST_CNT") or 0,
    )


def _build_sbr(raw: dict) -> SbrData:
    return SbrData(
        head_num=raw.get("HEAD_NUM"),
        site_num=raw.get("SITE_NUM") or 0,
        sbin_num=raw.get("SBIN_NUM") or 0,
        sbin_cnt=raw.get("SBIN_CNT") or 0,
        sbin_pf=raw.get("SBIN_PF"),
        sbin_nam=(raw.get("SBIN_NAM") or "").strip() or None,
    )


def _build_hbr(raw: dict) -> HbrData:
    return HbrData(
        head_num=raw.get("HEAD_NUM"),
        site_num=raw.get("SITE_NUM") or 0,
        hbin_num=raw.get("HBIN_NUM") or 0,
        hbin_cnt=raw.get("HBIN_CNT") or 0,
        hbin_pf=raw.get("HBIN_PF"),
        hbin_nam=(raw.get("HBIN_NAM") or "").strip() or None,
    )


class _Collector:
    def __init__(self):
        self.mir = None
        self.mrr = None
        self.pcr_list = []
        self.sbr_list = []
        self.hbr_list = []
        self.pir_count = 0
        self.prr_pass = 0
        self.prr_fail = 0
        self.prr_aborted = 0
        self.soft_bins = {}
        self.no_bin = 0
        self.raw_mir = None

    def after_send(self, ds, data):
        rec_type, fields = data

        if isinstance(rec_type, V4.Mir):
            raw = _to_dict(rec_type, fields)
            self.mir = _build_mir(raw)
            self.raw_mir = raw
        elif isinstance(rec_type, V4.Mrr):
            raw = _to_dict(rec_type, fields)
            self.mrr = _build_mrr(raw)
        elif isinstance(rec_type, V4.Pcr):
            raw = _to_dict(rec_type, fields)
            self.pcr_list.append(_build_pcr(raw))
        elif isinstance(rec_type, V4.Sbr):
            raw = _to_dict(rec_type, fields)
            self.sbr_list.append(_build_sbr(raw))
        elif isinstance(rec_type, V4.Hbr):
            raw = _to_dict(rec_type, fields)
            self.hbr_list.append(_build_hbr(raw))
        elif isinstance(rec_type, V4.Pir):
            self.pir_count += 1
        elif isinstance(rec_type, V4.Prr):
            d = _to_dict(rec_type, fields)
            if (d.get("PART_FLG", 0) & 1) == 0:
                self.prr_pass += 1
            else:
                self.prr_fail += 1
            if d.get("PART_FLG", 0) & 0x10:
                self.prr_aborted += 1
            sb = d.get("SOFT_BIN")
            if sb is not None:
                if sb == 65535:
                    self.no_bin += 1
                else:
                    self.soft_bins[sb] = self.soft_bins.get(sb, 0) + 1


def parse_stdf_bz2(bz2_path: str):
    collector = _Collector()

    with bz2.open(bz2_path, "rb") as f:
        parser = Parser(recTypes=NEEDED_TYPES, inp=f)
        parser.addSink(collector)
        parser.parse()

    return (
        collector.mir,
        collector.mrr,
        collector.pcr_list,
        collector.sbr_list,
        collector.hbr_list,
        collector.pir_count,
        collector.prr_pass,
        collector.prr_fail,
        collector.prr_aborted,
        collector.soft_bins,
        collector.no_bin,
    )


# ── analyzer ────────────────────────────────────────────────────────────────

def analyze(
    mir: MirData | None,
    mrr: MrrData | None,
    pcr_list: list[PcrData],
    sbr_list: list[SbrData],
    hbr_list: list[HbrData],
    pir_count: int,
    prr_pass: int,
    prr_fail: int,
    prr_aborted: int,
    soft_bins: dict[int, int],
    no_bin: int,
    file_path: str = "",
) -> AnalysisResult:
    return AnalysisResult(
        mir=mir, mrr=mrr,
        pcr_list=pcr_list, sbr_list=sbr_list, hbr_list=hbr_list,
        pir_count=pir_count,
        prr_pass=prr_pass, prr_fail=prr_fail, prr_aborted=prr_aborted,
        soft_bins=soft_bins, no_bin=no_bin,
        file_path=file_path,
    )


def compute_totals(result: AnalysisResult):
    total_parts = sum(p.part_cnt for p in result.pcr_list)
    total_good = sum(p.good_cnt for p in result.pcr_list)
    total_func_fail = sum(p.func_cnt for p in result.pcr_list)
    total_abort = sum(p.abort_cnt for p in result.pcr_list)
    total_retest = sum(p.retest_cnt for p in result.pcr_list)
    return total_parts, total_good, total_func_fail, total_abort, total_retest


def compute_yield(result: AnalysisResult) -> float | None:
    if not result.sbr_list or not result.pcr_list:
        return None
    total_parts = sum(p.part_cnt for p in result.pcr_list)
    if total_parts == 0:
        return None
    bin1 = next(
        (s.sbin_cnt for s in result.sbr_list if s.sbin_num == 1),
        0,
    )
    return bin1 / total_parts * 100


# ── formatter ───────────────────────────────────────────────────────────────

def _fmt_head(h: int | None) -> str:
    return "ALL" if h == 255 else str(h)


def _bin_pf(pf: int | None) -> str:
    if pf == 1:
        return "PASS"
    if pf == 0:
        return "FAIL"
    return ""


def print_report(result: AnalysisResult) -> None:
    sep = "=" * 60
    print(f"\n{sep}")
    print("STDF FILE ANALYSIS")
    print(sep)

    mir = result.mir
    mrr = result.mrr

    if mir:
        print(f"\n--- Master Information Record (MIR) ---")
        print(f"  Lot ID          : {mir.lot_id}")
        print(f"  Part Type       : {mir.part_type}")
        print(f"  Program Name    : {mir.job_name}")
        if mir.job_rev:
            print(f"  Job Revision    : {mir.job_rev}")
        print(f"  Tester Type     : {mir.tester_type}")
        print(f"  Node Name       : {mir.node_name}")
        print(f"  Operator Name   : {mir.operator_name}")
        print(f"  Test Temperature: {mir.test_temp} C")
        print(f"  Facility ID     : {mir.facility_id or 'N/A'}")
        print(f"  Floor ID        : {mir.floor_id or 'N/A'}")
        print(f"  Exec Type       : {mir.exec_type or 'N/A'}")
        print(f"  User Text       : {mir.user_text or 'N/A'}")

        if mir.start_t is not None:
            dt = datetime.fromtimestamp(mir.start_t, tz=timezone.utc)
            print(f"  Start Time      : {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        if mir.setup_t is not None:
            dt = datetime.fromtimestamp(mir.setup_t, tz=timezone.utc)
            print(f"  Setup Time      : {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    if mrr:
        print(f"\n--- Master Results Record (MRR) ---")
        if mrr.finish_t is not None:
            dt = datetime.fromtimestamp(mrr.finish_t, tz=timezone.utc)
            print(f"  Finish Time     : {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        if mir and mir.start_t is not None and mrr.finish_t is not None:
            duration = mrr.finish_t - mir.start_t
            print(f"  Test Duration   : {duration} seconds  ({duration / 60:.1f} min)")

    total_parts, total_good, total_func_fail, total_abort, total_retest = compute_totals(result)

    print(f"\n--- Part Counts ---")
    print(f"  PIR records (devices started) : {result.pir_count}")

    if result.pcr_list:
        print(f"  PCR records (head/site groups): {len(result.pcr_list)}")
        print(f"  Total parts (summed)          : {total_parts}")
        if total_good:
            print(f"  Total good                    : {total_good}")
        if total_func_fail:
            print(f"  Total functional fail         : {total_func_fail}")
        if total_abort:
            print(f"  Total abort                   : {total_abort}")
        if total_retest:
            print(f"  Total retest                  : {total_retest}")

    print(f"  PRR records (device results)  : {result.prr_pass + result.prr_fail}")
    print(f"  PRR passed (bit0=0)           : {result.prr_pass}")
    print(f"  PRR failed (bit0=1)           : {result.prr_fail}")
    print(f"  PRR aborted (bit4=1)          : {result.prr_aborted}")
    print(f"  Distinct soft bins seen       : {len(result.soft_bins)}")
    if result.no_bin:
        print(f"  Devices w/o final bin (65535) : {result.no_bin}")

    yield_pct = compute_yield(result)
    if yield_pct is not None:
        print(f"  Yield (bin1/total)            : {yield_pct:.2f}%")

    print(f"\n--- Software Bin Summary (SBR) ---")
    if result.sbr_list:
        sbr_sorted = sorted(result.sbr_list, key=lambda r: r.sbin_num)
        total_sbr = 0
        for sbr in sbr_sorted:
            head = _fmt_head(sbr.head_num)
            cnt = sbr.sbin_cnt
            pf = _bin_pf(sbr.sbin_pf)
            name = sbr.sbin_nam or ""
            total_sbr += cnt
            print(f"    H={head} S={sbr.site_num}  Bin={sbr.sbin_num:>4}  Count={cnt:>6}  {pf:>4}  {name}")
        print(f"    {'Total':>19}  Count={total_sbr:>6}")
    else:
        print("  (none)")

    print(f"\n--- Hardware Bin Summary (HBR) ---")
    if result.hbr_list:
        hbr_sorted = sorted(result.hbr_list, key=lambda r: r.hbin_num)
        total_hbr = 0
        for hbr in hbr_sorted:
            head = _fmt_head(hbr.head_num)
            cnt = hbr.hbin_cnt
            pf = _bin_pf(hbr.hbin_pf)
            name = hbr.hbin_nam or ""
            total_hbr += cnt
            print(f"    H={head} S={hbr.site_num}  Bin={hbr.hbin_num:>4}  Count={cnt:>6}  {pf:>4}  {name}")
        print(f"    {'Total':>19}  Count={total_hbr:>6}")
    else:
        print("  (none)")

    print(f"\n{sep}")
    print("Analysis complete.")
    print(sep)


# ── entry point ─────────────────────────────────────────────────────────────

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
