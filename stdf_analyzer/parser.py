import bz2

from pystdf.IO import Parser
from pystdf import V4

from stdf_analyzer.models import MirData, MrrData, PcrData, SbrData, HbrData

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
