# III. Data and Preprocessing

**Source.** Seven annual Vaisala FALLS exports for the Situbondo--
Banyuwangi line cover calendar years 2019 through 2025. Each export
contains 29 worksheets in a mixed schema: a yearly per-tower exposure
sheet, a per-month time-trend sheet (renamed `2023_Timetrend` in the
2023 file --- a known irregularity), and a per-strike peak-current
histogram with year-varying bin widths (1&nbsp;kA in 2022 versus 5&nbsp;kA
elsewhere). Tower geolocation comes from a separate coordinate file
containing 281 TOWER entries plus 282 SPAN entries; the SPANs are
filtered out at the tidy stage.

**Preprocessing.** A standalone `tidy_data.py` script normalises the
29-sheet workbook into seven flat CSVs and a plain-text audit report.
Quality checks (35/35 passing on the v1.2 build) include: 281 unique
tower IDs with no gaps in the range 1--281; exactly $7 \times 281 =
1{,}967$ panel rows; set equality between the tower-coordinate file
and the panel-exposure file; non-negative counts; and latitude/longitude
sanity bounds. The aggregate row ("All selected assets") that prefixes
each Vaisala export is discarded explicitly to prevent double counting.

**The Vaisala density convention.** A material data caveat: the
panel-aggregate annual strike count is empirically a factor of **4.94
to 5.19** larger than the line-aggregate unique-strike count, across
all seven years. The most likely explanation is that each strike falls
inside the 3.125&nbsp;km$^2$ collection circle of approximately five
adjacent towers and is counted by each, producing an overlap-count
ratio close to five. The per-tower density-to-count ratio is empirically
**0.32 = 1/3.125&nbsp;km$^{-2}$** across every (tower, year) cell --- a
constant geometric factor that confirms the overlap-counting
interpretation but does not by itself resolve the convention. We
therefore work at the panel scale throughout and disclose this as an
unresolved Vaisala-side question in &sect;VII.

**Climate covariates.** Monthly Niño&nbsp;3.4 SST anomalies are fetched
from the NOAA Physical Sciences Laboratory plain-text endpoint [11];
the Indian Ocean Dipole DMI index is fetched from the HadISST mirror
on the same server [12]. We aggregate both to seasonal JJA means per
year. Per-tower elevation comes from the Open-Meteo elevation API,
cached locally to support offline reproducibility.

**Public release.** All seven tidy CSVs, the cached climate parquets,
and the entire processing pipeline are published in the source
repository [13].
