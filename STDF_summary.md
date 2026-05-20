# STDF V4 — 2007 Specification Summary

**Standard Test Data Format** — binary format for semiconductor test data interchange between ATE and EDA/diagnosis tools.

---

## Purpose

Provide a common format for **scan fail datalog** with synchronization information enabling efficient **volume diagnosis** workflows. Extends the original STDF V4 to support structural test failures (scan, memory BIST) for yield learning.

Key design goals:
- Capture millions of failures per device
- Support wafer-level and package-level test
- Enable design-test-design feedback loop
- Works alongside existing STDF V4 data flows

---

## File Structure

Every STDF V4-2007 file begins with an **initial sequence**:

```
FAR — [ATRs] — VUR — MIR — [RDR] — [SDRs]
```

| Record | Name | Required | Description |
|---|---|---|---|
| FAR | File Attributes Record | Yes | First record in file |
| ATR | Audit Trail Record | No | Change history |
| VUR | Version Update Record | Yes | Identifies as V4-2007 (`UPD_NAM = "V4-2007"`) |
| MIR | Master Information Record | Yes | Lot-level setup, tester, program info |
| RDR | Retest Data Record | No | |
| SDR | Site Description Record | No | Per-site configuration |

All other records appear **after** the initial sequence.

---

## Major Record Types

| REC_TYP | Group | Subtypes (REC_SUB) |
|---|---|---|
| **0** | File info | FAR(10), ATR(20), **VUR**(30) |
| **1** | Per lot | MIR(10), MRR(20), PCR(30), HBR(40), SBR(50), PMR(60), PGR(62), PLR(63), RDR(70), SDR(80), **PSR**(90), **NMR**(91), **CNR**(92), **SSR**(93), **SCR**(94) |
| **2** | Per wafer | WIR(10), WRR(20), WCR(30) |
| **5** | Per part | **PIR**(10), **PRR**(20) |
| **10** | Per test program | TSR(30) |
| **15** | Per test execution | PTR(10), MPR(15), FTR(20), **STR**(30) |
| **20** | Per program segment | BPS(10), EPS(20) |
| **50** | Generic | GDR(10), DTR(30) |

**Bold** = new or extended for V4-2007.

---

## New V4-2007 Records (Scan Fail Support)

### VUR — Version Update Record (REC_TYP=0, REC_SUB=30)
- Required record identifying the file as V4-2007
- Single field: `UPD_NAM` (set to `"V4-2007"`)

### PSR — Pattern Sequence Record (REC_TYP=1, REC_SUB=90)
- Describes how ATPG patterns are assembled for a scan test (test pattern map)
- Supports **continuation records** (REC_INDX/REC_TOT) when data exceeds 65 KB
- Key fields: `PSR_NAM`, `TOTP_CNT`/`LOCP_CNT`, arrays of `PAT_FILE`, `PAT_BGN`, `PAT_END`
- Optional: `PAT_LBL` (symbolic pattern name), `FILE_UID` (unique file ID), `ATPG_DSC`, `SRC_ID`

### NMR — Name Map Record (REC_TYP=1, REC_SUB=91)
- Maps PMR indexes to ATPG signal names (for pins not named in PMR records)
- Fields: `PMR_INDX[]`, `ATPG_NAM[]`

### CNR — Scan Cell Name Record (REC_TYP=1, REC_SUB=92)
- Maps (Chain #, Bit Position) → flip-flop/cell name
- Fields: `CHN_NUM`, `BIT_POS`, `CELL_NAM`

### SSR — Scan Structure Record (REC_TYP=1, REC_SUB=93)
- Top-level scan structure — references SCR records via `CHN_LIST`
- Fields: `SSR_NAM`, `CHN_CNT`, `CHN_LIST[]`

### SCR — Scan Chain Description Record (REC_TYP=1, REC_SUB=94)
- Describes a single scan chain: scan-in pin, scan-out pin, clocks, cell names
- Fields: `SCR_INDX`, `CHN_NAM`, `TOTS_CNT`/`LOCS_CNT`, `SIN_PIN`, `SOUT_PIN`, `M_CLKS[]`, `S_CLKS[]`, `INV_VAL`, `CELL_LST[]`

### STR — Scan Test Record (REC_TYP=15, REC_SUB=30)
- Core record for per-test-execution scan fail data
- Structure:

| Section | Key Fields |
|---|---|
| Header | `TEST_NUM`, `HEAD_NUM`, `SITE_NUM`, `PSR_REF`, `TEST_FLG` |
| Condition | `COND_CNT`, `COND_NAM[]`, `COND_VAL[]` |
| Validation | `CYC_CNT`, `TOTF_CNT`, `TOTL_CNT`, `CYC_BASE`, `BIT_BASE` |
| Mask/Fail Map | `MASK_MAP`, `FAL_MAP`, `FMU_FLG` |
| Datalog | `CYCL_NUM[]`, `PMR_INDX[]`, `CHN_NUM[]`, `CAP_DATA[]`, `EXP_DATA[]`, `NEW_DATA[]`, `PAT_NUM[]`, `BIT_POS[]` |
| User | `USR1/2/3[]`, `USER_TXT[]` |

- Supports **continuation records** for large fail sets
- Configurable via `DATA_FLG` — each bit enables/disables a datalog array
- Two logging modes: **Cycle-based** (CYC_NUM + PMR_INDX) and **Pattern-based** (PAT_NUM + BIT_POS)

---

## Data Type Codes

| Code | Description | Size |
|---|---|---|
| `U*1,2,4,8` | Unsigned integer | 1,2,4,8 bytes |
| `I*1,2,4` | Signed integer | 1,2,4 bytes |
| `R*4,8` | Float / double | 4,8 bytes |
| `C*n` | Variable string (1-byte length) | max 255 bytes |
| `S*n` | Variable string (2-byte length) | max 65,535 bytes |
| `B*n` | Bit-encoded (1-byte count) | max 255 bytes |
| `D*n` | Bit-encoded (2-byte count) | max 65,535 bits |
| `kxTYPE` | Array of TYPE, count = earlier field | variable |

---

## Continuation Records

When a data set exceeds 65,536 bytes per record, it is split across multiple records using:

- **REC_INDX** — current record index (1-based within the set)
- **REC_TOT** — total records in the set
- Global/local count fields (e.g., `TOTP_CNT`/`LOCP_CNT`) — readers concatenate arrays across continuation records

---

## Optional / Missing Data

- Variable-length strings: set length byte to 0
- Fixed strings: fill with spaces
- Numeric fields: use reserved sentinel (e.g., 65535, 4,294,967,295) or Optional Data flag bits
- First missing optional field does **not** imply rest are missing (new for V4-2007)

---

## Key Data Model Objects

| Data Object | STDF Records |
|---|---|
| Design Netlist Rev | MIR.DSGN_REV |
| Scan Structure | SSR → SCR |
| Device ID | MIR, WIR/WRR, PRR |
| Tester/Facility | MIR, SDR |
| Test Program | MIR |
| Test Suite / Pattern Map | PSR |
| Test Conditions | STR (COND_NAM/VAL) |
| Fail Data | STR |
| Pin Name Map | NMR |

---

## Use Models

The standard supports three coexistence modes:
1. STDF V4 with **no scan fail data** (existing usage)
2. STDF V4 with **existing + scan fail** information
3. STDF V4 with **scan fail information only**

---

## File Size Considerations

- STR records can consume the most space (potentially millions of failures)
- SCR records with full `CELL_LST` can also be very large
- Continuation records mitigate the 65 KB per-record limit

---

## References

- IEEE 1450 (STIL) — Standard Test Interface Language
- STDF V4 base specification (pre-2007)
- ATDF — ASCII text representation of STDF
