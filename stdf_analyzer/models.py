from dataclasses import dataclass, field
from typing import Optional


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
class TsrData:
    head_num: Optional[int]
    site_num: int
    test_typ: str
    test_num: int
    exec_cnt: int
    fail_cnt: int
    alrm_cnt: int
    test_nam: Optional[str]
    seq_name: Optional[str]
    test_lbl: Optional[str]
    test_tim: Optional[float]
    test_min: Optional[float]
    test_max: Optional[float]
    tst_sums: Optional[float]
    tst_sqrs: Optional[float]


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
