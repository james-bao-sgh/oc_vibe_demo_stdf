#!/usr/bin/env python3
"""Standalone STDF analyzer — single file, no local dependencies."""

from __future__ import annotations

import bz2
import struct
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


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


# ── parser (custom tight-loop STDF reader) ──────────────────────────────────

# STDF record types we care about
_REC_MIR = (1, 10)
_REC_MRR = (1, 20)
_REC_PCR = (1, 30)
_REC_HBR = (1, 40)
_REC_SBR = (1, 50)
_REC_PIR = (5, 10)
_REC_PRR = (5, 20)


def _u1(buf, pos, end, endian, default=0):
    return struct.unpack_from(endian + 'B', buf, pos)[0] if pos + 1 <= end else default

def _u2(buf, pos, end, endian, default=0):
    return struct.unpack_from(endian + 'H', buf, pos)[0] if pos + 2 <= end else default

def _u4(buf, pos, end, endian, default=0):
    return struct.unpack_from(endian + 'I', buf, pos)[0] if pos + 4 <= end else default

def _cn(buf, pos, end, endian):
    """Read Cn (variable string) if within bounds. Returns (value, new_pos)."""
    if pos >= end:
        return None, pos
    slen = buf[pos]
    pos += 1
    if slen == 0 or pos + slen > end:
        return None, pos
    return buf[pos:pos + slen].decode('ascii', errors='replace'), pos + slen


def _parse_mir(buf, pos, end, endian):
    """Parse MIR record, return MirData."""
    setup_t = _u4(buf, pos, end, endian); pos += 4
    start_t = _u4(buf, pos, end, endian); pos += 4
    pos += 1  # STAT_NUM
    pos += 1  # MODE_COD
    pos += 1  # RTST_COD
    pos += 1  # PROT_COD
    pos += 2  # BURN_TIM
    pos += 1  # CMOD_COD
    lot_id, pos = _cn(buf, pos, end, endian)
    part_type, pos = _cn(buf, pos, end, endian)
    node_name, pos = _cn(buf, pos, end, endian)
    tester_type, pos = _cn(buf, pos, end, endian)
    job_name, pos = _cn(buf, pos, end, endian)
    job_rev, pos = _cn(buf, pos, end, endian)
    _, pos = _cn(buf, pos, end, endian)  # SBLOT_ID (skip)
    operator_name, pos = _cn(buf, pos, end, endian)
    exec_type, pos = _cn(buf, pos, end, endian)
    _, pos = _cn(buf, pos, end, endian)  # EXEC_VER (skip)
    _, pos = _cn(buf, pos, end, endian)  # TEST_COD (skip)
    test_temp_raw, pos = _cn(buf, pos, end, endian)
    user_text, pos = _cn(buf, pos, end, endian)
    _, pos = _cn(buf, pos, end, endian)  # AUX_FILE (skip)
    _, pos = _cn(buf, pos, end, endian)  # PKG_TYP (skip)
    _, pos = _cn(buf, pos, end, endian)  # FAMLY_ID (skip)
    _, pos = _cn(buf, pos, end, endian)  # DATE_COD (skip)
    facility_id, pos = _cn(buf, pos, end, endian)
    floor_id, pos = _cn(buf, pos, end, endian)

    test_temp = test_temp_raw.strip() if test_temp_raw else None

    return MirData(
        lot_id=lot_id or "",
        part_type=part_type or "",
        job_name=job_name or "",
        job_rev=job_rev,
        tester_type=tester_type or "",
        node_name=node_name or "",
        operator_name=operator_name or "",
        test_temp=test_temp,
        facility_id=facility_id,
        floor_id=floor_id,
        exec_type=exec_type,
        user_text=user_text,
        start_t=start_t if start_t != 0 else None,
        setup_t=setup_t if setup_t != 0 else None,
    )


def _parse_mrr(buf, pos, end, endian):
    """Parse MRR record, return MrrData."""
    finish_t = _u4(buf, pos, end, endian)
    return MrrData(finish_t=finish_t if finish_t != 0 else None)


def _parse_pcr(buf, pos, end, endian):
    """Parse PCR record, return PcrData."""
    head_num = _u1(buf, pos, end, endian); pos += 1
    site_num = _u1(buf, pos, end, endian); pos += 1
    part_cnt = _u4(buf, pos, end, endian); pos += 4
    retest_cnt = _u4(buf, pos, end, endian, default=0); pos += 4
    abort_cnt = _u4(buf, pos, end, endian, default=0); pos += 4
    good_cnt = _u4(buf, pos, end, endian, default=0); pos += 4
    func_cnt = _u4(buf, pos, end, endian, default=0); pos += 4
    return PcrData(
        head_num=head_num, site_num=site_num,
        part_cnt=part_cnt, good_cnt=good_cnt,
        func_cnt=func_cnt, abort_cnt=abort_cnt,
        retest_cnt=retest_cnt,
    )


def _parse_hbr(buf, pos, end, endian):
    """Parse HBR record, return HbrData."""
    head_num = _u1(buf, pos, end, endian); pos += 1
    site_num = _u1(buf, pos, end, endian); pos += 1
    hbin_num = _u2(buf, pos, end, endian); pos += 2
    hbin_cnt = _u4(buf, pos, end, endian); pos += 4
    hbin_pf_raw = _u1(buf, pos, end, endian); pos += 1
    hbin_nam, pos = _cn(buf, pos, end, endian)
    return HbrData(
        head_num=head_num, site_num=site_num,
        hbin_num=hbin_num, hbin_cnt=hbin_cnt,
        hbin_pf=hbin_pf_raw if hbin_pf_raw != 0 else None,
        hbin_nam=hbin_nam.strip() if hbin_nam else None,
    )


def _parse_sbr(buf, pos, end, endian):
    """Parse SBR record, return SbrData."""
    head_num = _u1(buf, pos, end, endian); pos += 1
    site_num = _u1(buf, pos, end, endian); pos += 1
    sbin_num = _u2(buf, pos, end, endian); pos += 2
    sbin_cnt = _u4(buf, pos, end, endian); pos += 4
    sbin_pf_raw = _u1(buf, pos, end, endian); pos += 1
    sbin_nam, pos = _cn(buf, pos, end, endian)
    return SbrData(
        head_num=head_num, site_num=site_num,
        sbin_num=sbin_num, sbin_cnt=sbin_cnt,
        sbin_pf=sbin_pf_raw if sbin_pf_raw != 0 else None,
        sbin_nam=sbin_nam.strip() if sbin_nam else None,
    )


def parse_stdf_bz2(bz2_path: str):
    # Decompress entire file to memory
    with bz2.open(bz2_path, "rb") as f:
        buf = f.read()

    # Detect endianness from FAR record (first record)
    # FAR:  REC_TYP=0, REC_SUB=10, data has CPU_TYPE at offset 4
    # CPU_TYPE 1=big, 2=little
    far_cpu = buf[4] if len(buf) > 4 else 2
    endian = '>' if far_cpu == 1 else '<'

    pos = 0
    n = len(buf)

    mir = None
    mrr = None
    pcr_list = []
    sbr_list = []
    hbr_list = []
    pir_count = 0
    prr_pass = 0
    prr_fail = 0
    prr_aborted = 0
    soft_bins: dict[int, int] = {}
    no_bin = 0

    while pos + 4 <= n:
        rec_len, rec_typ, rec_sub = struct.unpack_from(endian + 'HBB', buf, pos)
        pos += 4
        data_end = pos + rec_len

        key = (rec_typ, rec_sub)

        if key == _REC_MIR:
            mir = _parse_mir(buf, pos, data_end, endian)
        elif key == _REC_MRR:
            mrr = _parse_mrr(buf, pos, data_end, endian)
        elif key == _REC_PCR:
            pcr_list.append(_parse_pcr(buf, pos, data_end, endian))
        elif key == _REC_HBR:
            hbr_list.append(_parse_hbr(buf, pos, data_end, endian))
        elif key == _REC_SBR:
            sbr_list.append(_parse_sbr(buf, pos, data_end, endian))
        elif key == _REC_PIR:
            pir_count += 1
        elif key == _REC_PRR:
            # Only need PART_FLG and SOFT_BIN
            part_flg_val = _u1(buf, pos + 2, data_end, endian, default=0)
            if (part_flg_val & 1) == 0:
                prr_pass += 1
            else:
                prr_fail += 1
            if part_flg_val & 0x10:
                prr_aborted += 1
            sb_val = _u2(buf, pos + 6, data_end, endian, default=65535)
            if sb_val == 65535:
                no_bin += 1
            else:
                soft_bins[sb_val] = soft_bins.get(sb_val, 0) + 1

        pos = data_end

    return (
        mir, mrr, pcr_list, sbr_list, hbr_list,
        pir_count, prr_pass, prr_fail, prr_aborted,
        soft_bins, no_bin,
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
