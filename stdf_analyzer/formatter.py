from datetime import datetime, timezone

from stdf_analyzer.models import AnalysisResult
from stdf_analyzer.analyzer import compute_totals, compute_yield


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
