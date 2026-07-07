"""
voc/parser.py
CSV validation, parsing, and deduplication for VOC performance data.

All functions are pure Python / Pandas — no Streamlit imports.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS: list[str] = [
    "Wbr Carrier Group",
    "Year ID",
    "Vendor Code",
    "Vendor Name",
    "Week ID",
    "PDD Shipment #",
    "DEA %",
    "Unpadded DEA %",
]

COLUMN_RENAME_MAP: dict[str, str] = {
    "Wbr Carrier Group": "wbr_carrier_group",
    "Year ID": "year_id",
    "Vendor Code": "vendor_code",
    "Vendor Name": "vendor_name",
    "Week ID": "week_id",
    "PDD Shipment #": "pdd_shipments",
    "DEA %": "dea_pct",
    "Unpadded DEA %": "unpadded_dea_pct",
}

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ParseResult:
    """Result of a parse_voc_csv() call."""

    df: pd.DataFrame
    warnings: list[str] = field(default_factory=list)
    total_ingested: int = 0
    total_skipped: int = 0
    week_id_range: tuple[int, int] | None = None


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def validate_header(headers: list[str]) -> list[str]:
    """
    Return a sorted list of required column names that are absent from *headers*.

    Returns an empty list when all required columns are present (valid header).
    Returns a non-empty list of exactly the missing column names otherwise.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in headers]
    return sorted(missing)


def parse_pdd(raw: str) -> int | None:
    """
    Parse a PDD Shipment # string to a non-negative integer.

    Strips surrounding whitespace and internal commas (e.g. "24,708" → 24708).
    Returns None if the value is empty, non-numeric, negative, or a decimal.
    """
    cleaned = raw.strip().replace(",", "")
    if not cleaned:
        return None
    try:
        val = float(cleaned)
    except ValueError:
        return None
    # Reject decimals and negatives
    if val != int(val) or val < 0:
        return None
    return int(val)


def parse_dea(raw: str) -> float | None:
    """
    Parse a DEA % string to a fraction in [0.0, 1.0].

    Accepts strings like "97.0%", "100.0%", "0.0%".
    Returns None if the string lacks a "%" suffix, is non-numeric,
    or the numeric value is outside [0.0, 100.0].
    """
    stripped = raw.strip()
    if not stripped.endswith("%"):
        return None
    cleaned = stripped[:-1]
    try:
        val = float(cleaned)
    except ValueError:
        return None
    if val < 0.0 or val > 100.0:
        return None
    return val / 100.0


def parse_voc_csv(csv_text: str) -> ParseResult:
    """
    Full parse pipeline for a VOC performance CSV string.

    Steps:
      1. Read with pandas.read_csv (dtype=str to prevent auto-conversion).
      2. Validate header via validate_header(); raise ValueError listing
         missing columns if the header is invalid.
      3. Rename columns using COLUMN_RENAME_MAP; drop the optional leading
         row-index column if present.
      4. Iterate rows; call parse_pdd / parse_dea; skip invalid rows and
         append warning strings containing the 1-based row number and
         the raw field value.
      5. Identify duplicates on (vendor_code, week_id); warn per duplicate,
         then retain first occurrence.
      6. Cast surviving columns to int64 / float64.
      7. Populate and return ParseResult.

    Raises:
        ValueError: if required columns are missing (file-level error).
    """
    warnings: list[str] = []

    # --- Step 1: read raw CSV (all columns as strings) ---
    try:
        raw_df = pd.read_csv(io.StringIO(csv_text), dtype=str)
    except Exception as exc:
        raise ValueError(f"Could not read CSV: {exc}") from exc

    # --- Step 2: validate header ---
    missing = validate_header(list(raw_df.columns))
    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(missing)}"
        )

    # --- Step 3: drop optional index column, rename ---
    # The VOC export contains an unnamed leading index column. Drop it.
    if raw_df.columns[0] not in COLUMN_RENAME_MAP:
        raw_df = raw_df.drop(columns=[raw_df.columns[0]])

    raw_df = raw_df.rename(columns=COLUMN_RENAME_MAP)

    # --- Steps 4 & 5: row-level validation and deduplication ---
    valid_rows: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()
    total_skipped = 0

    for row_idx, row in enumerate(raw_df.itertuples(index=False), start=2):
        # 1-based data row number (row 1 = header, row 2 = first data row)
        row_num = row_idx

        vendor_code = str(row.vendor_code).strip()
        vendor_name = str(row.vendor_name).strip()
        wbr = str(row.wbr_carrier_group).strip()
        year_raw = str(row.year_id).strip()
        week_raw = str(row.week_id).strip()
        pdd_raw = str(row.pdd_shipments).strip()
        dea_raw = str(row.dea_pct).strip()
        udea_raw = str(row.unpadded_dea_pct).strip()

        # Validate PDD
        pdd_val = parse_pdd(pdd_raw)
        if pdd_val is None:
            warnings.append(
                f"Row {row_num}: invalid PDD Shipment # value '{pdd_raw}' — row skipped."
            )
            total_skipped += 1
            continue

        # Validate DEA %
        dea_val = parse_dea(dea_raw)
        if dea_val is None:
            warnings.append(
                f"Row {row_num}: invalid DEA % value '{dea_raw}' — row skipped."
            )
            total_skipped += 1
            continue

        # Validate Unpadded DEA %
        udea_val = parse_dea(udea_raw)
        if udea_val is None:
            warnings.append(
                f"Row {row_num}: invalid Unpadded DEA % value '{udea_raw}' — row skipped."
            )
            total_skipped += 1
            continue

        # Validate year and week as integers
        try:
            year_val = int(float(year_raw))
            week_val = int(float(week_raw))
        except (ValueError, TypeError):
            warnings.append(
                f"Row {row_num}: invalid Year ID or Week ID ('{year_raw}', '{week_raw}') — row skipped."
            )
            total_skipped += 1
            continue

        # Deduplication: (vendor_code, week_id) — keep first
        key = (vendor_code, week_raw)
        if key in seen_keys:
            warnings.append(
                f"Row {row_num}: duplicate (vendor_code='{vendor_code}', week_id={week_val}) — row skipped."
            )
            total_skipped += 1
            continue
        seen_keys.add(key)

        valid_rows.append(
            {
                "wbr_carrier_group": wbr,
                "year_id": year_val,
                "vendor_code": vendor_code,
                "vendor_name": vendor_name,
                "week_id": week_val,
                "pdd_shipments": pdd_val,
                "dea_pct": dea_val,
                "unpadded_dea_pct": udea_val,
            }
        )

    # --- Step 6: build final DataFrame with correct dtypes ---
    if valid_rows:
        df = pd.DataFrame(valid_rows)
        df = df.astype(
            {
                "year_id": "int64",
                "week_id": "int64",
                "pdd_shipments": "int64",
                "dea_pct": "float64",
                "unpadded_dea_pct": "float64",
            }
        )
        week_id_range: tuple[int, int] | None = (
            int(df["week_id"].min()),
            int(df["week_id"].max()),
        )
    else:
        df = pd.DataFrame(
            columns=[
                "wbr_carrier_group",
                "year_id",
                "vendor_code",
                "vendor_name",
                "week_id",
                "pdd_shipments",
                "dea_pct",
                "unpadded_dea_pct",
            ]
        )
        week_id_range = None

    total_ingested = len(df)

    return ParseResult(
        df=df,
        warnings=warnings,
        total_ingested=total_ingested,
        total_skipped=total_skipped,
        week_id_range=week_id_range,
    )


# ---------------------------------------------------------------------------
# Excel parser — handles SODA fct_df_ops_performance exports
# DEA/Unpadded DEA values are already fractions [0.0, 1.0], not "XX.X%" strings
# ---------------------------------------------------------------------------


def parse_voc_excel(file_bytes: bytes) -> "ParseResult":
    """
    Parse a SODA-format Excel (.xlsx) VOC performance export.

    Accepts the same schema as parse_voc_csv but expects:
    - DEA % and Unpadded DEA % as float fractions [0.0, 1.0] (not percentage strings)
    - PDD Shipment # as plain integers (no comma-formatting)

    Returns a ParseResult with the same structure as parse_voc_csv.
    Raises ValueError if required columns are missing.
    """
    warnings: list[str] = []

    try:
        raw_df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, dtype=str)
    except Exception as exc:
        raise ValueError(f"Could not read Excel file: {exc}") from exc

    # Validate header
    missing = validate_header(list(raw_df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    # Drop optional leading index column if present
    if raw_df.columns[0] not in COLUMN_RENAME_MAP:
        raw_df = raw_df.drop(columns=[raw_df.columns[0]])

    raw_df = raw_df.rename(columns=COLUMN_RENAME_MAP)

    valid_rows: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()
    total_skipped = 0

    for row_idx, row in enumerate(raw_df.itertuples(index=False), start=2):
        row_num = row_idx

        vendor_code = str(row.vendor_code).strip()
        vendor_name = str(row.vendor_name).strip()
        wbr         = str(row.wbr_carrier_group).strip()
        year_raw    = str(row.year_id).strip()
        week_raw    = str(row.week_id).strip()
        pdd_raw     = str(row.pdd_shipments).strip()
        dea_raw     = str(row.dea_pct).strip()
        udea_raw    = str(row.unpadded_dea_pct).strip()

        # PDD — plain integer (no commas expected from Excel)
        pdd_val = parse_pdd(pdd_raw.replace(",", ""))
        if pdd_val is None:
            warnings.append(f"Row {row_num}: invalid PDD Shipment # '{pdd_raw}' — row skipped.")
            total_skipped += 1
            continue

        # DEA — already a fraction [0.0, 1.0] in Excel; validate and use directly
        # Also handles "XX.X%" strings in case the file has mixed format
        dea_val  = _parse_dea_excel(dea_raw, row_num, warnings)
        udea_val = _parse_dea_excel(udea_raw, row_num, warnings)
        if dea_val is None or udea_val is None:
            total_skipped += 1
            continue

        try:
            year_val = int(float(year_raw))
            week_val = int(float(week_raw))
        except (ValueError, TypeError):
            warnings.append(f"Row {row_num}: invalid Year/Week ('{year_raw}', '{week_raw}') — row skipped.")
            total_skipped += 1
            continue

        key = (vendor_code, week_raw)
        if key in seen_keys:
            warnings.append(f"Row {row_num}: duplicate (vendor_code='{vendor_code}', week_id={week_val}) — row skipped.")
            total_skipped += 1
            continue
        seen_keys.add(key)

        valid_rows.append({
            "wbr_carrier_group": wbr,
            "year_id": year_val,
            "vendor_code": vendor_code,
            "vendor_name": vendor_name,
            "week_id": week_val,
            "pdd_shipments": pdd_val,
            "dea_pct": dea_val,
            "unpadded_dea_pct": udea_val,
        })

    if valid_rows:
        df = pd.DataFrame(valid_rows).astype({
            "year_id": "int64", "week_id": "int64",
            "pdd_shipments": "int64",
            "dea_pct": "float64", "unpadded_dea_pct": "float64",
        })
        week_id_range: tuple[int, int] | None = (int(df["week_id"].min()), int(df["week_id"].max()))
    else:
        df = pd.DataFrame(columns=[
            "wbr_carrier_group", "year_id", "vendor_code", "vendor_name",
            "week_id", "pdd_shipments", "dea_pct", "unpadded_dea_pct",
        ])
        week_id_range = None

    return ParseResult(
        df=df,
        warnings=warnings,
        total_ingested=len(df),
        total_skipped=total_skipped,
        week_id_range=week_id_range,
    )


def _parse_dea_excel(raw: str, row_num: int, warnings: list[str]) -> float | None:
    """
    Parse a DEA value from Excel that may be:
    - A fraction string like "0.9700" (SODA default)
    - A percentage string like "97.0%" (CSV-style)

    Returns a fraction [0.0, 1.0] or None on failure.
    """
    s = raw.strip().rstrip("%")
    try:
        val = float(s)
    except ValueError:
        return None

    # If value looks like a percentage (> 1.0), convert to fraction
    if val > 1.0:
        if val > 100.0:
            return None
        return val / 100.0

    # Already a fraction [0.0, 1.0]
    if val < 0.0:
        return None
    return val
