"""
voc/export.py
CSV export generation for filtered VOC data.

All functions are pure Python / Pandas — no Streamlit imports.
"""
from __future__ import annotations

import pandas as pd

from voc.formatters import format_dea, format_pdd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Internal column names, in required export order
EXPORT_COLUMNS_ORDER: list[str] = [
    "vendor_code",
    "vendor_name",
    "week_id",
    "pdd_shipments",
    "dea_pct",
    "unpadded_dea_pct",
]

# Display header names that map 1-to-1 with EXPORT_COLUMNS_ORDER
EXPORT_HEADER: list[str] = [
    "Vendor Code",
    "Vendor Name",
    "Week ID",
    "PDD Shipment #",
    "DEA %",
    "Unpadded DEA %",
]

# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def records_to_csv(df: pd.DataFrame) -> str:
    """
    Convert a filtered records DataFrame to a RFC-4180 compliant CSV string.

    Column order follows EXPORT_HEADER.
    PDD Shipment # is formatted with thousands separators (e.g. "24,708").
    DEA % and Unpadded DEA % are formatted as "XX.X%" strings.
    Fields containing commas are automatically wrapped in double-quotes
    by pandas' to_csv().

    Returns a header-only CSV string when *df* is empty.

    Satisfies Property 20 (export round-trip correctness).
    """
    if df.empty:
        return ",".join(EXPORT_HEADER) + "\r\n"

    out = df[EXPORT_COLUMNS_ORDER].copy()

    # Format display values
    out["pdd_shipments"] = out["pdd_shipments"].apply(format_pdd)
    out["dea_pct"] = out["dea_pct"].apply(format_dea)
    out["unpadded_dea_pct"] = out["unpadded_dea_pct"].apply(format_dea)

    # Rename to export header names
    out.columns = EXPORT_HEADER  # type: ignore[assignment]

    return out.to_csv(index=False, lineterminator="\r\n")


def generate_export_bytes(df: pd.DataFrame) -> bytes:
    """
    Return records_to_csv(df) encoded as UTF-8 bytes for st.download_button.
    """
    return records_to_csv(df).encode("utf-8")


def export_filename(dt: object) -> str:
    """
    Generate a timestamped filename for CSV exports.

    Parameters
    ----------
    dt : datetime
        The timestamp to embed (typically datetime.now()).

    Returns
    -------
    str
        e.g. "voc_export_20260615_143022.csv"
    """
    return dt.strftime("voc_export_%Y%m%d_%H%M%S.csv")
