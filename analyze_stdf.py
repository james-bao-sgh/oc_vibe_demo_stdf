#!/usr/bin/env python3
"""Extract basic info from a bz2-compressed STDF file using pystdf."""

import bz2
import sys
from datetime import datetime, timezone

from pystdf.IO import Parser
from pystdf import V4

NEEDED_TYPES = [r for r in V4.records if r.__class__ in (
    V4.Mir, V4.Mrr, V4.Pcr, V4.Sbr, V4.Hbr, V4.Pir, V4.Prr)]


def fmt_head(h):
    return "ALL" if h == 255 else str(h)


def bin_pf(pf):
    if pf == 1:
        return "PASS"
    if pf == 0:
        return "FAIL"
    return ""


def analyze_stdf_bz2(bz2_path: str):
    print(f"Opening: {bz2_path}")

    def to_dict(rec, fields):
        return {k: v for (k, _), v in zip(rec.fieldMap, fields)}

    mir = None
    mrr = None
    pcr_list = []
    sbr_list = []
    hbr_list = []
    pir_count = 0
    prr_pass = 0
    prr_fail = 0
    prr_aborted = 0
    soft_bins = {}
    no_bin = 0

    class Collector:
        def after_send(self, ds, data):
            nonlocal mir, mrr, pir_count, prr_pass, prr_fail, prr_aborted, no_bin
            rec_type, fields = data

            if isinstance(rec_type, V4.Mir):
                mir = to_dict(rec_type, fields)
            elif isinstance(rec_type, V4.Mrr):
                mrr = to_dict(rec_type, fields)
            elif isinstance(rec_type, V4.Pcr):
                pcr_list.append(to_dict(rec_type, fields))
            elif isinstance(rec_type, V4.Sbr):
                sbr_list.append(to_dict(rec_type, fields))
            elif isinstance(rec_type, V4.Hbr):
                hbr_list.append(to_dict(rec_type, fields))
            elif isinstance(rec_type, V4.Pir):
                pir_count += 1
            elif isinstance(rec_type, V4.Prr):
                d = to_dict(rec_type, fields)
                if (d.get("PART_FLG", 0) & 1) == 0:
                    prr_pass += 1
                else:
                    prr_fail += 1
                if d.get("PART_FLG", 0) & 0x10:
                    prr_aborted += 1
                sb = d.get("SOFT_BIN")
                if sb is not None:
                    if sb == 65535:
                        no_bin += 1
                    else:
                        soft_bins[sb] = soft_bins.get(sb, 0) + 1

    with bz2.open(bz2_path, "rb") as f:
        parser = Parser(recTypes=NEEDED_TYPES, inp=f)
        parser.addSink(Collector())
        parser.parse()

    sep = "=" * 60
    print(f"\n{sep}")
    print("STDF FILE ANALYSIS")
    print(sep)

    if mir:
        print(f"\n--- Master Information Record (MIR) ---")
        print(f"  Lot ID          : {mir['LOT_ID']}")
        print(f"  Part Type       : {mir['PART_TYP']}")
        print(f"  Program Name    : {mir['JOB_NAM']}")
        rev = mir.get("JOB_REV")
        if rev:
            print(f"  Job Revision    : {rev}")
        print(f"  Tester Type     : {mir['TSTR_TYP']}")
        print(f"  Node Name       : {mir['NODE_NAM']}")
        print(f"  Operator Name   : {mir['OPER_NAM']}")
        print(f"  Test Temperature: {mir['TST_TEMP']} C")
        print(f"  Facility ID     : {mir.get('FACIL_ID') or 'N/A'}")
        print(f"  Floor ID        : {mir.get('FLOOR_ID') or 'N/A'}")
        print(f"  Exec Type       : {mir.get('EXEC_TYP') or 'N/A'}")
        print(f"  User Text       : {mir.get('USER_TXT') or 'N/A'}")

        start_ts = mir.get("START_T")
        if start_ts is not None:
            dt = datetime.fromtimestamp(start_ts, tz=timezone.utc)
            print(f"  Start Time      : {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        setup_ts = mir.get("SETUP_T")
        if setup_ts is not None:
            dt = datetime.fromtimestamp(setup_ts, tz=timezone.utc)
            print(f"  Setup Time      : {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    if mrr:
        print(f"\n--- Master Results Record (MRR) ---")
        finish_ts = mrr.get("FINISH_T")
        if finish_ts is not None:
            dt = datetime.fromtimestamp(finish_ts, tz=timezone.utc)
            print(f"  Finish Time     : {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        if start_ts and finish_ts:
            duration = finish_ts - start_ts
            print(f"  Test Duration   : {duration} seconds  ({duration / 60:.1f} min)")

    print(f"\n--- Part Counts ---")
    print(f"  PIR records (devices started) : {pir_count}")

    if pcr_list:
        total_parts = sum((p.get("PART_CNT") or 0) for p in pcr_list)
        total_good = sum((p.get("GOOD_CNT") or 0) for p in pcr_list)
        total_fail = sum((p.get("FUNC_CNT") or 0) for p in pcr_list)
        total_abort = sum((p.get("ABRT_CNT") or 0) for p in pcr_list)
        total_retest = sum((p.get("RTST_CNT") or 0) for p in pcr_list)
        print(f"  PCR records (head/site groups): {len(pcr_list)}")
        print(f"  Total parts (summed)          : {total_parts}")
        if total_good:
            print(f"  Total good                    : {total_good}")
        if total_fail:
            print(f"  Total functional fail         : {total_fail}")
        if total_abort:
            print(f"  Total abort                   : {total_abort}")
        if total_retest:
            print(f"  Total retest                  : {total_retest}")

    print(f"  PRR records (device results)  : {prr_pass + prr_fail}")
    print(f"  PRR passed (bit0=0)           : {prr_pass}")
    print(f"  PRR failed (bit0=1)           : {prr_fail}")
    print(f"  PRR aborted (bit4=1)          : {prr_aborted}")
    print(f"  Distinct soft bins seen       : {len(soft_bins)}")
    if no_bin:
        print(f"  Devices w/o final bin (65535) : {no_bin}")

    if sbr_list and total_parts:
        bin1 = next((s.get("SBIN_CNT", 0) or 0) for s in sbr_list if s.get("SBIN_NUM") == 1)
        yield_pct = bin1 / total_parts * 100
        print(f"  Yield (bin1/total)            : {yield_pct:.2f}%")

    print(f"\n--- Software Bin Summary (SBR) ---")
    if sbr_list:
        sbr_sorted = sorted(sbr_list, key=lambda r: r.get("SBIN_NUM", 0) or 0)
        total_sbr = 0
        for sbr in sbr_sorted:
            head = fmt_head(sbr.get("HEAD_NUM", 255))
            site = sbr.get("SITE_NUM", 0)
            sbin = sbr.get("SBIN_NUM", 0)
            cnt = sbr.get("SBIN_CNT", 0) or 0
            pf = bin_pf(sbr.get("SBIN_PF"))
            name = (sbr.get("SBIN_NAM") or "").strip()
            total_sbr += cnt
            print(f"    H={head} S={site}  Bin={sbin:>4}  Count={cnt:>6}  {pf:>4}  {name}")
        print(f"    {'Total':>19}  Count={total_sbr:>6}")
    else:
        print("  (none)")

    print(f"\n--- Hardware Bin Summary (HBR) ---")
    if hbr_list:
        hbr_sorted = sorted(hbr_list, key=lambda r: r.get("HBIN_NUM", 0) or 0)
        total_hbr = 0
        for hbr in hbr_sorted:
            head = fmt_head(hbr.get("HEAD_NUM", 255))
            site = hbr.get("SITE_NUM", 0)
            hbin = hbr.get("HBIN_NUM", 0)
            cnt = hbr.get("HBIN_CNT", 0) or 0
            pf = bin_pf(hbr.get("HBIN_PF"))
            name = (hbr.get("HBIN_NAM") or "").strip()
            total_hbr += cnt
            print(f"    H={head} S={site}  Bin={hbin:>4}  Count={cnt:>6}  {pf:>4}  {name}")
        print(f"    {'Total':>19}  Count={total_hbr:>6}")
    else:
        print("  (none)")

    print(f"\n{sep}")
    print("Analysis complete.")
    print(sep)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_stdf.py <path-to-bz2-file>")
        sys.exit(1)
    analyze_stdf_bz2(sys.argv[1])
