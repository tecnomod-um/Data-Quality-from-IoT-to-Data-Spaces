# Historical reference-table recovery and descriptive agreement — H2022

**Version 1.1.0. This package recovers historical tabulated observations and adds descriptive paired comparisons using author-confirmed measurement units.** H2022 names the report's May 2022 cover date. The literal annex timestamps include 2019, 2021 and 2022. The author confirmed that these reports are related to the paper and authorized their use. This establishes a source relationship; an exact cohort, record or physical-device mapping to the paper's 171 metrics remains unverified. The historical observations are retained as a distinct evidence layer and do not replace those metrics or their stated campaign dates.

The package contains 12,610 timestamped rows in eight pollutant series. Of these, 12,168 contain both a sensor value and a reference value. Seven pollutants supply 7,370 complete pairs with author-confirmed units. PM1 supplies a further 4,798 complete pairs on an unconfirmed numerical scale. All 442 incomplete rows belong to PM1: 75 sensor cells and 373 reference cells are blank; six rows have both cells blank. Missing cells are retained as empty CSV fields. No values are interpolated, recalibrated, corrected, removed as outliers or numerically converted.

## Source and provenance

The source is a 1085-page PDF, report revision 2, cover dated May 2022. Its SHA-256 is:

`f0da594d8506e937ed9134840687c746ebb099a354440b7c5062b981b28b4234`

The original PDF and its Drive inventory are retained separately in the private preparation material. They are not included here. The PDF contains an embedded signature field with a May 12, 2023 timestamp; presence of a field is not verification of the signature, certificate trust, or validity at signing.

HS1–HS8 identify historical table series, not eight physical devices. `device_identity` and `reference_identity` remain null. No mapping to D1–D3, or between sensors in different series, is established. Neutral column names remove direct manufacturer and author labels from this package, but no claim of anonymity or public redistribution license is made.

## Recovered rows

Dates below follow the annexes. UTC offsets are explicit for NO2, NO, O3, SO2 and PM1. CO and particulate PM10/PM2.5 rows do not state a timezone.

| Series | Pollutant | Rows | Complete pairs | Literal annex time extent | PDF pages |
|---|---|---:|---:|---|---|
| HS1 | NO2 | 800 | 800 | 2021-11-18 17:00 to 2021-12-22 17:00, +00:00 | 30–98 |
| HS2 | NO | 788 | 788 | 2022-01-13 01:00 to 2022-02-17 16:00, +00:00 | 98–161 |
| HS3 | O3 | 774 | 774 | 2021-11-18 17:00 to 2021-12-22 09:00, +00:00 | 162–224 |
| HS4 | SO2 | 535 | 535 | 2022-02-01 00:00 to 2022-03-01 04:00, +00:00 | 224–267 |
| HS5 | CO | 29 | 29 | 2/26/19 8:00 to 2/28/19 12:00, timezone unspecified | 268–270 |
| HS6 | PM10 | 2222 | 2222 | 2022-01-12 17:00 to 2022-04-26 05:00, timezone unspecified | 270–427 |
| HS7 | PM2.5 | 2222 | 2222 | 2022-01-12 17:00 to 2022-04-26 05:00, timezone unspecified | 427–584 |
| HS8 | PM1 | 5240 | 4798 | 2022-01-17 00:00 to 2022-01-20 15:19, +00:00 | 584–1085 |

The modal interval is one hour for HS1–HS7 and one minute for HS8. There are no duplicate timestamps within a series. Diagnostic regular grids between each annex's first and last timestamp contain 17, 68, 35, 142, 24, 263, 263 and 0 unlisted instants, respectively. These counts describe gaps in the printed annex, not the completeness of the original campaign. CO contains only printed hours 1–12; the source does not establish whether its original clock format was 12-hour or 24-hour. Normalized timestamps retain the literal hour interpretation and are flagged for clarification.

## Author annotation and remaining restrictions

Annotation `H2022-A1`, recorded on 28 October 2026, documents the author's confirmation. `reported_unit` remains null because the annex headings omit units. A separate `effective_unit` is `ug/m3` for NO2, NO, O3, SO2, PM10 and PM2.5, and `mg/m3` for CO. Its basis is explicitly `author_confirmation`; these units were not silently inserted into the source transcription or inferred from the numerical range. The annotation applies to both columns of each pair.

The exact author answers retained in that annotation are “I confirm they are related use them” and “Confirmed the units are the same.” The second answer is interpreted as confirmation of the measurement units used in the paper, not as a physical serial-number mapping or a correction of conflicting dates and summaries. This interpretation and its limits are explicit in the machine-readable metadata.

PM1 is outside the original seven-pollutant corpus and its physical unit was not confirmed. Its `effective_unit` remains null. The source's general PM1 methodology refers to `ug/m2` on pages 5 and 11; that ambiguous statement is not corrected or treated as confirmation of a concentration unit.

The unit restriction is removed for the seven confirmed pollutants, permitting descriptive paired comparison. Remaining `quarantine_flags` apply to uses requiring unresolved physical identity, exact cohort linkage, date/station consistency or source-summary interpretation. They do not forbid describing the pairs as printed. PM1 remains restricted to unit-free association and explicitly labelled arithmetic on the unconfirmed numerical scale. This package does not support a conformity classification, calibration transfer or reconstruction of expanded uncertainty.

The following conflicts remain unresolved:

| Conflict | Body of report | Annex / other location | Treatment |
|---|---|---|---|
| NO2 dates | Page 19: 13 Jan–17 Feb 2022 | Pages 30–98: 18 Nov–22 Dec 2021 | Preserve annex dates; flag conflict |
| NO2 reference station | Page 19 lists a station code different from the NO2 station designated on page 10 | The annex does not independently establish the station | Leave reference identity null |
| SO2 dates | Page 25: 18 Nov–22 Dec 2021 | Pages 224–267: 1 Feb–1 Mar 2022 | Preserve annex dates; flag conflict |
| CO year | Page 27: 26–28 Feb 2022 | Pages 268–270 print 26–28 Feb 2019 | Preserve `19`; flag year and clock ambiguity |
| PM10 uncertainty | Page 14: 11% | Page 29: 10% | No uncertainty attached to observations |
| NO2 uncertainty | Page 20: 20% | Page 29: 12% | No uncertainty attached to observations |
| NO uncertainty | Page 22: 12% | Page 29: 21% | No uncertainty attached to observations |
| SO2 R-squared | Page 26: 0.85 | Page 29: 0.61; reported r is 0.78 | No summary correction or inferential use |
| Annex numbering | PM10 heading calls itself Annex III on page 270 | O3 already uses Annex III on page 162 | Use pollutant and physical PDF page as locators |

The PDF reports uncertainty percentages in its body and summary but does not provide an unambiguous per-row uncertainty budget or coverage factor for these annexes. A separately retrieved methods paper explicitly uses k=2 in a different analysis; that value has not been transferred here. The author's measurement-unit confirmation does not establish a coverage factor, resolve the current NO limit 50 or SO2 threshold basis, or supply a D1–D3 serial map. It also does not establish that these annexes are the exact observation cohorts behind all five report classes in the 171-record corpus.

## Descriptive analysis

For each pollutant, complete rows are used with equal weight and with the sensor/reference pairing exactly as printed. Bias is the mean of sensor minus reference; MAE is the mean absolute difference; RMSE is the square root of the mean squared difference. Pearson correlation describes association. OLS is explicitly oriented as `sensor = intercept + slope × reference`. Its fit is descriptive and is not applied as a calibration or correction. Each series has nonzero reference variance, so the numerical fit is identifiable; three distinct reference values in SO2 and CO still limit its interpretation.

No new temporal join, lag correction, reweighting, outlier removal or imputation is performed. Annex dates are preserved despite the documented conflicts. The row count is not an independent sample count: serial dependence, gaps and the unknown selection mechanism remain relevant. No confidence intervals or significance tests are reported. RMSE is a descriptive difference statistic and is not substituted for expanded measurement uncertainty.

The exact results and limitations are in `data/paired_agreement_metrics.csv` and `.json`. `docs/evidence_memo.md` presents the compact table and interpretation. PM1 dimensional arithmetic is explicitly separated in that memo, with no physical unit assigned. `data/largest_absolute_errors.csv` retains source locators for the three largest absolute differences per series; these rows were not diagnosed as invalid or removed.

`data/regression_direction_diagnostics.csv` records both OLS directions. Most summary slopes on source page 29 are nearer reference-on-sensor fits than sensor-on-reference fits. This proximity does not prove an identical population or fitting method, and some values do not reproduce at the reported rounding. It prevents a misleading direct comparison of slopes with different orientations.

## Files

`data/H2022_paired_observations.csv` contains every recovered row, including incomplete rows. Eight pollutant-specific CSVs provide the same rows by series. `data/extraction_summary.json` records counts, dates, interval frequencies, missing cells, provenance and caveats. `data/extraction_rejects.json` is empty because every printed date row was recovered. `data/verification.json` records the independent PDF-word comparison. `docs/author_annotations.json` records the author confirmation; `data/annotation_verification.json` proves that all 18 protected source columns are unchanged. `data/analysis_verification.json` records independent high-precision numerical checks. See `docs/data_dictionary.md` for field meanings and `docs/source_manifest.json` for the source manifest.

## Reproduce

Use Python 3, Poppler's `pdftotext`, and PyMuPDF. The captured run used pdftotext 24.02.0 and PyMuPDF 1.26.6. Supply the original source privately; its hash must match exactly.

```sh
python scripts/extract_historical_tables.py /path/to/H2022_source.pdf
python scripts/annotate_historical_units.py
python scripts/analyze_historical_agreement.py
python scripts/verify_historical_tables.py /path/to/H2022_source.pdf
python scripts/verify_historical_analysis.py
```

The extractor preserves printed numeric strings and literal dates, records page/row provenance, and uses PDF word coordinates only to determine which PM1 cell is blank. The independent verifier compares every recovered timestamp and numeric value with a second PDF text engine. It matched all 12,610 source rows with zero unmatched rows or numeric discrepancies. Representative first-row, boundary and missing-cell pages were also inspected visually. This confirms transcription integrity, not metrological correctness.

Author-confirmed units support the descriptive analysis documented here. Attribution to a specific certified device, reconstruction of uncertainty, conformity assessment or transfer to the current cohorts still requires the unresolved dates, identities and report-budget provenance to be supplied. The 171 metric records and captured prototype results remain unchanged.
