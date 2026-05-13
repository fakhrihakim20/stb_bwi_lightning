"""
tidy_data.py — Convert the messy lightning Excel workbooks into clean tidy CSVs.

Reads:
  Lightning Exposure Line Situbondo-Banyuwangi YoY.xlsx (29 sheets, 2019-2025)
  koordinat tower srintami.xlsx (281 TOWERs + 282 SPANs)

Writes to ./data_tidy/:
  exposure_tower_year.csv   per-tower yearly stats (1,967 rows = 7 yr * 281 towers)
  exposure_line_year.csv    whole-line yearly aggregate (7 rows)
  monthly_line.csv          monthly line totals (~84 rows)
  peak_current_hist.csv     kA histograms per year (native bin width preserved)
  towers.csv                281 tower coordinates
  spans.csv                 282 span coordinates
  _data_quality_report.txt  human-readable audit
  _2025_completeness.flag   written only if 2025 looks partial

Run:  python tidy_data.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
LIGHTNING_XLSX = HERE / "Lightning Exposure Line Situbondo-Banyuwangi YoY.xlsx"
TOWERS_XLSX = HERE / "koordinat tower srintami.xlsx"
OUT_DIR = HERE / "data_tidy"

YEARS = list(range(2019, 2026))


EXPOSURE_RENAME = {
    "Name": "tower_id",
    "Count": "count",
    "Count (-)": "count_neg",
    "Count (+)": "count_pos",
    "% Positive": "pct_positive",
    "Density": "density",
    "Min kA": "min_ka",
    "Max kA": "max_ka",
    "Mean kA": "mean_ka",
    "Min kA (-)": "min_ka_neg",
    "Max kA (-)": "max_ka_neg",
    "Mean kA (-)": "mean_ka_neg",
    "Min kA (+)": "min_ka_pos",
    "Max kA (+)": "max_ka_pos",
    "Mean kA (+)": "mean_ka_pos",
    "Exp. factor": "exp_factor",
}

TIMETREND_RENAME = {
    "From": "period_start",
    "To": "period_end",
    "Count": "count",
    "Count (-)": "count_neg",
    "Count (+)": "count_pos",
    "% (+)": "pct_positive",
}

PEAKCURRENT_RENAME = {
    "From (kA)": "ka_from",
    "To (kA)": "ka_to",
    "Count (-)": "count_neg",
    "Count (+)": "count_pos",
    "Cumul. (-)": "cum_neg",
    "Cumul. (+)": "cum_pos",
    "% (-)": "pct_neg",
    "% (+)": "pct_pos",
    "Cumul. % (-)": "cum_pct_neg",
    "Cumul. % (+)": "cum_pct_pos",
}


class Audit:
    """Accumulate human-readable audit notes plus pass/fail counts."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.checks_passed = 0
        self.checks_failed = 0

    def section(self, title: str) -> None:
        self.lines.append("")
        self.lines.append("=" * 72)
        self.lines.append(title)
        self.lines.append("=" * 72)

    def note(self, msg: str) -> None:
        self.lines.append(msg)

    def check(self, passed: bool, msg: str) -> None:
        prefix = "[PASS]" if passed else "[FAIL]"
        self.lines.append(f"{prefix} {msg}")
        if passed:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

    def write(self, path: Path) -> None:
        header = [
            "Lightning Data Quality Audit",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            f"Checks passed: {self.checks_passed}",
            f"Checks failed: {self.checks_failed}",
        ]
        path.write_text("\n".join(header + self.lines), encoding="utf-8")


def tidy_exposure(xls: pd.ExcelFile, audit: Audit) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (per-tower long panel, whole-line yearly aggregate)."""

    audit.section("EXPOSURE SHEETS (yearly per-tower stats)")
    tower_frames: list[pd.DataFrame] = []
    line_frames: list[pd.DataFrame] = []

    for year in YEARS:
        sheet = f"{year}_Exposure"
        if sheet not in xls.sheet_names:
            audit.check(False, f"missing sheet {sheet}")
            continue
        df = xls.parse(sheet)
        audit.note(f"{sheet}: raw shape {df.shape}, columns={list(df.columns)}")

        missing_cols = [c for c in EXPOSURE_RENAME if c not in df.columns]
        if missing_cols:
            audit.check(False, f"{sheet}: missing columns {missing_cols}")
            continue
        df = df.rename(columns=EXPOSURE_RENAME)

        # Split aggregate row 0 ("All selected assets") from per-tower rows.
        is_aggregate = df["tower_id"].astype(str).str.contains("selected", case=False, na=False)
        agg_df = df.loc[is_aggregate].copy()
        tower_df = df.loc[~is_aggregate].copy()

        audit.check(len(agg_df) == 1, f"{sheet}: exactly one aggregate row (found {len(agg_df)})")
        audit.check(
            len(tower_df) == 281,
            f"{sheet}: exactly 281 per-tower rows (found {len(tower_df)})",
        )

        # tower_id should be integer 1..281.
        tower_df["tower_id"] = pd.to_numeric(tower_df["tower_id"], errors="coerce").astype("Int64")
        bad_ids = tower_df["tower_id"].isna().sum()
        audit.check(bad_ids == 0, f"{sheet}: all tower_id parse to integers ({bad_ids} bad)")

        tower_df["year"] = year
        agg_df["year"] = year
        agg_df = agg_df.drop(columns=["tower_id"])

        # Coerce numeric columns.
        num_cols = [c for c in EXPOSURE_RENAME.values() if c != "tower_id"]
        for c in num_cols:
            tower_df[c] = pd.to_numeric(tower_df[c], errors="coerce")
            if c in agg_df.columns:
                agg_df[c] = pd.to_numeric(agg_df[c], errors="coerce")

        tower_frames.append(tower_df)
        line_frames.append(agg_df)

    tower_panel = pd.concat(tower_frames, ignore_index=True)
    # Order columns: ids first.
    id_cols = ["tower_id", "year"]
    other_cols = [c for c in tower_panel.columns if c not in id_cols]
    tower_panel = tower_panel[id_cols + other_cols].sort_values(["year", "tower_id"]).reset_index(drop=True)

    line_panel = pd.concat(line_frames, ignore_index=True)
    line_panel = line_panel[["year"] + [c for c in line_panel.columns if c != "year"]]
    line_panel = line_panel.sort_values("year").reset_index(drop=True)

    audit.check(
        len(tower_panel) == 7 * 281,
        f"tower panel has 7*281 = 1967 rows (found {len(tower_panel)})",
    )
    audit.check(
        tower_panel.groupby("year")["tower_id"].nunique().eq(281).all(),
        "every year has exactly 281 unique towers",
    )

    # Diagnostic only: exp_factor in this dataset is negative and not simply
    # the IEEE 1410 effective collection area (Count != Density * Exp.factor).
    # Log the empirical implied area (Count / Density) so the modeling notebook
    # can choose the correct exposure offset.
    nonzero = (tower_panel["count"] > 0) & (tower_panel["density"] > 0)
    implied_area = tower_panel.loc[nonzero, "count"] / tower_panel.loc[nonzero, "density"]
    audit.note(
        f"Implied collection area (Count / Density) [km^2]: "
        f"mean {implied_area.mean():.3f}, median {implied_area.median():.3f}, "
        f"std {implied_area.std():.3f}, range [{implied_area.min():.3f}, {implied_area.max():.3f}]"
    )
    audit.note(
        f"exp_factor (software-specific, NEGATIVE): "
        f"mean {tower_panel['exp_factor'].mean():.2f}, "
        f"range [{tower_panel['exp_factor'].min():.2f}, {tower_panel['exp_factor'].max():.2f}]. "
        f"Do NOT use as a simple area multiplier; treat as opaque covariate."
    )

    # No NaNs in core count columns.
    core_cols = ["count", "count_neg", "count_pos", "density", "exp_factor"]
    n_nan = tower_panel[core_cols].isna().sum().sum()
    audit.check(n_nan == 0, f"no NaNs in core count/density columns (found {n_nan})")

    # No negative counts.
    neg_counts = (tower_panel[["count", "count_neg", "count_pos"]] < 0).any().any()
    audit.check(not neg_counts, "no negative count values")

    return tower_panel, line_panel


def tidy_monthly(xls: pd.ExcelFile, audit: Audit) -> pd.DataFrame:
    """Return monthly line panel with explicit year tag and partial-month flag."""

    audit.section("TIME TREND SHEETS (monthly whole-line)")
    pattern = re.compile(r"^(\d{4})_Time\s?[Tt]rend$")
    frames: list[pd.DataFrame] = []
    found_years = set()

    for sheet in xls.sheet_names:
        m = pattern.match(sheet)
        if not m:
            continue
        year = int(m.group(1))
        df = xls.parse(sheet)
        audit.note(f"{sheet}: raw shape {df.shape}, columns={list(df.columns)}")

        missing = [c for c in TIMETREND_RENAME if c not in df.columns]
        if missing:
            audit.check(False, f"{sheet}: missing columns {missing}")
            continue
        df = df.rename(columns=TIMETREND_RENAME)
        df["period_start"] = pd.to_datetime(df["period_start"], errors="coerce")
        df["period_end"] = pd.to_datetime(df["period_end"], errors="coerce")
        df["year"] = year
        df["month"] = df["period_start"].dt.month
        # Partial if period straddles or starts in a different year.
        df["is_partial_month"] = (
            (df["period_start"].dt.year != year) | (df["period_end"].dt.year != year)
        )
        for c in ["count", "count_neg", "count_pos", "pct_positive"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        frames.append(df)
        found_years.add(year)

    missing_years = [y for y in YEARS if y not in found_years]
    audit.check(
        len(missing_years) == 0,
        f"all {len(YEARS)} years have Time Trend sheet (missing: {missing_years})",
    )

    if not frames:
        audit.note("no time trend sheets parsed — returning empty DataFrame")
        return pd.DataFrame(
            columns=["year", "month", "period_start", "period_end",
                     "count", "count_neg", "count_pos", "pct_positive", "is_partial_month"]
        )

    out = pd.concat(frames, ignore_index=True)
    cols = ["year", "month", "period_start", "period_end",
            "count", "count_neg", "count_pos", "pct_positive", "is_partial_month"]
    out = out[cols].sort_values(["year", "period_start"]).reset_index(drop=True)
    audit.note(f"monthly panel: {len(out)} rows across {out['year'].nunique()} years")
    return out


def tidy_peak_current(xls: pd.ExcelFile, audit: Audit) -> pd.DataFrame:
    """Return long-form kA histogram with native bin width preserved per year."""

    audit.section("PEAK CURRENT SHEETS (kA histograms)")
    frames: list[pd.DataFrame] = []
    for year in YEARS:
        sheet = f"{year}_Peak Current"
        if sheet not in xls.sheet_names:
            audit.check(False, f"missing sheet {sheet}")
            continue
        df = xls.parse(sheet)
        audit.note(f"{sheet}: raw shape {df.shape}, columns={list(df.columns)}")

        missing = [c for c in PEAKCURRENT_RENAME if c not in df.columns]
        if missing:
            audit.check(False, f"{sheet}: missing columns {missing}")
            continue
        df = df.rename(columns=PEAKCURRENT_RENAME)
        df["year"] = year
        for c in PEAKCURRENT_RENAME.values():
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["bin_width"] = (df["ka_to"] - df["ka_from"]).round(3)
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    cols = ["year", "ka_from", "ka_to", "bin_width",
            "count_neg", "count_pos", "cum_neg", "cum_pos",
            "pct_neg", "pct_pos", "cum_pct_neg", "cum_pct_pos"]
    out = out[cols].sort_values(["year", "ka_from"]).reset_index(drop=True)

    bw_by_year = out.groupby("year")["bin_width"].agg(lambda s: s.dropna().mode().iloc[0])
    audit.note("native kA bin width by year:")
    for y, bw in bw_by_year.items():
        audit.note(f"  {y}: {bw} kA")
    return out


def tidy_coords(audit: Audit) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split coordinate file into towers (281) and spans (282)."""

    audit.section("TOWER COORDINATE FILE")
    df = pd.read_excel(TOWERS_XLSX)
    audit.note(f"raw shape {df.shape}, columns={list(df.columns)}")

    audit.check(
        {"NAMA", "LAT", "LNG"}.issubset(df.columns),
        "coordinate file has NAMA, LAT, LNG columns",
    )

    # Drop duplicate LOCK columns if present.
    drop_cols = [c for c in ("LOCK LAT", "LOCK LNG") if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)
        audit.note(f"dropped redundant columns: {drop_cols}")

    is_tower = df["NAMA"].str.contains("TOWER", case=False, na=False)
    is_span = df["NAMA"].str.contains("SPAN", case=False, na=False)
    audit.check(is_tower.sum() == 281, f"exactly 281 TOWER rows (found {is_tower.sum()})")
    audit.check(is_span.sum() == 282, f"exactly 282 SPAN rows (found {is_span.sum()})")
    audit.check(
        (is_tower | is_span).all(),
        "every row is either TOWER or SPAN (no orphans)",
    )

    # Towers: extract the first integer after '#'. Most names end with #NNNN,
    # but the parallel-circuit GLNK3,4 section uses #NNN/M (e.g. #280/2) where
    # NNN is still the tower id and /M is the parallel-circuit index.
    tower_df = df.loc[is_tower].copy()
    tower_df["tower_id"] = (
        tower_df["NAMA"].str.extract(r"#(\d+)", expand=False).astype("Int64")
    )
    audit.check(
        tower_df["tower_id"].notna().all(),
        "all tower NAMA strings have an extractable #NNN id",
    )
    audit.check(
        tower_df["tower_id"].nunique() == 281
        and tower_df["tower_id"].min() == 1
        and tower_df["tower_id"].max() == 281,
        "tower IDs are exactly 1..281 with no gaps",
    )

    # Spans: extract whatever follows '#'.
    span_df = df.loc[is_span].copy()
    span_extract = span_df["NAMA"].str.extract(r"#(?P<from_tower>\d+)/(?P<to_tower>\d+)")
    span_df["from_tower"] = pd.to_numeric(span_extract["from_tower"], errors="coerce").astype("Int64")
    span_df["to_tower"] = pd.to_numeric(span_extract["to_tower"], errors="coerce").astype("Int64")
    span_df["span_id"] = range(1, len(span_df) + 1)

    # Geographic sanity bounds for East Java.
    lat_ok = tower_df["LAT"].between(-9, -7).all()
    lng_ok = tower_df["LNG"].between(113, 115).all()
    audit.check(lat_ok, "all tower LAT in [-9, -7]")
    audit.check(lng_ok, "all tower LNG in [113, 115]")

    tower_out = tower_df[["tower_id", "LAT", "LNG", "NAMA"]].rename(
        columns={"LAT": "lat", "LNG": "lng", "NAMA": "asset_name"}
    ).sort_values("tower_id").reset_index(drop=True)

    span_out = span_df[["span_id", "from_tower", "to_tower", "LAT", "LNG", "NAMA"]].rename(
        columns={"LAT": "lat", "LNG": "lng", "NAMA": "asset_name"}
    ).reset_index(drop=True)

    return tower_out, span_out


def cross_validate(
    tower_panel: pd.DataFrame,
    line_panel: pd.DataFrame,
    monthly: pd.DataFrame,
    towers: pd.DataFrame,
    audit: Audit,
) -> None:
    audit.section("CROSS-FILE VALIDATION")

    panel_ids = set(tower_panel["tower_id"].dropna().astype(int).unique())
    coord_ids = set(towers["tower_id"].dropna().astype(int).unique())

    audit.check(
        panel_ids == coord_ids,
        f"tower IDs match between exposure and coordinates "
        f"(panel: {len(panel_ids)}, coords: {len(coord_ids)}, "
        f"intersection: {len(panel_ids & coord_ids)})",
    )

    # 2025 completeness: compare Exposure aggregate vs monthly sum.
    line_2025 = line_panel.loc[line_panel["year"] == 2025, "count"]
    monthly_2025 = monthly.loc[
        (monthly["year"] == 2025) & (~monthly["is_partial_month"]),
        "count",
    ]
    if not line_2025.empty and not monthly_2025.empty:
        line_total = float(line_2025.iloc[0])
        monthly_total = float(monthly_2025.sum())
        rel = abs(line_total - monthly_total) / max(line_total, 1)
        audit.note(
            f"2025 reconciliation: exposure-line total = {line_total:.0f}, "
            f"monthly sum (non-partial) = {monthly_total:.0f}, "
            f"rel diff = {rel:.3f}"
        )
        if rel > 0.10:
            (OUT_DIR / "_2025_completeness.flag").write_text(
                f"2025 totals disagree: line={line_total}, monthly={monthly_total}, rel={rel:.3f}\n",
                encoding="utf-8",
            )
            audit.note("WROTE _2025_completeness.flag — 2025 may be partial.")


def main() -> int:
    if not LIGHTNING_XLSX.exists():
        print(f"ERROR: missing {LIGHTNING_XLSX}", file=sys.stderr)
        return 2
    if not TOWERS_XLSX.exists():
        print(f"ERROR: missing {TOWERS_XLSX}", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Clean any stale flag.
    flag = OUT_DIR / "_2025_completeness.flag"
    if flag.exists():
        flag.unlink()

    audit = Audit()
    audit.note(f"Source workbook: {LIGHTNING_XLSX.name}")
    audit.note(f"Source coordinates: {TOWERS_XLSX.name}")
    audit.note(f"Output directory: {OUT_DIR}")

    xls = pd.ExcelFile(LIGHTNING_XLSX)
    audit.note(f"workbook has {len(xls.sheet_names)} sheets")

    tower_panel, line_panel = tidy_exposure(xls, audit)
    monthly = tidy_monthly(xls, audit)
    peakcurr = tidy_peak_current(xls, audit)
    towers, spans = tidy_coords(audit)

    cross_validate(tower_panel, line_panel, monthly, towers, audit)

    tower_panel.to_csv(OUT_DIR / "exposure_tower_year.csv", index=False)
    line_panel.to_csv(OUT_DIR / "exposure_line_year.csv", index=False)
    monthly.to_csv(OUT_DIR / "monthly_line.csv", index=False)
    peakcurr.to_csv(OUT_DIR / "peak_current_hist.csv", index=False)
    towers.to_csv(OUT_DIR / "towers.csv", index=False)
    spans.to_csv(OUT_DIR / "spans.csv", index=False)

    audit.section("OUTPUTS")
    for f in sorted(OUT_DIR.iterdir()):
        if f.is_file():
            audit.note(f"  {f.name} ({f.stat().st_size:,} bytes)")

    audit.write(OUT_DIR / "_data_quality_report.txt")

    print(f"Wrote {len(list(OUT_DIR.iterdir()))} files to {OUT_DIR}")
    print(f"Checks passed: {audit.checks_passed} | failed: {audit.checks_failed}")
    if audit.checks_failed:
        print("See _data_quality_report.txt for details.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
