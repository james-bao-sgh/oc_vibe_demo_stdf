from stdf_analyzer.models import AnalysisResult, MirData, MrrData, PcrData, SbrData, HbrData


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
        mir=mir,
        mrr=mrr,
        pcr_list=pcr_list,
        sbr_list=sbr_list,
        hbr_list=hbr_list,
        pir_count=pir_count,
        prr_pass=prr_pass,
        prr_fail=prr_fail,
        prr_aborted=prr_aborted,
        soft_bins=soft_bins,
        no_bin=no_bin,
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
