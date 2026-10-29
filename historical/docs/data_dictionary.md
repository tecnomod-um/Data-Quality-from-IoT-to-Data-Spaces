# Data dictionary

Each CSV row is one timestamped row printed in a historical report annex. Empty strings mean null, never zero. Numeric strings retain the printed precision. Source-reported fields are preserved separately from author annotations: a null `reported_unit` can coexist with an author-confirmed `effective_unit`.

| Field | Type / interpretation |
|---|---|
| `dataset_id` | Constant `H2022`, denoting report cover date rather than observation year |
| `series_id` | `HS1`–`HS8`, an annex-series identifier; does not identify a physical device |
| `pollutant` | NO2, NO, O3, SO2, CO, PM10, PM2.5 or PM1, transcribed from annex heading |
| `device_identity` | Null; no conclusive sensor serial or linkage is encoded |
| `reference_identity` | Null; the annex does not independently establish a unique reference device and the body contains station inconsistencies |
| `source_row` | One-based chronological row number within that pollutant annex, including incomplete rows |
| `pdf_page` | One-based physical PDF page where the row starts |
| `pdf_page_end` | One-based physical PDF page where the row ends |
| `page_row` | One-based data-row ordinal within that pollutant series on that page; resets at each page |
| `timestamp_source` | Printed date and time joined with one space; timezone offset retained if explicitly printed |
| `timestamp_iso` | ISO representation without changing the clock value; CO `19` interpreted as 2019 and flagged because the body conflicts; no timezone supplied where absent |
| `timezone_status` | `explicit_UTC_offset` or `not_stated` |
| `sensor_value` | Literal decimal string in the sensor column, or null |
| `reference_value` | Literal decimal string in the reference column, or null |
| `pair_status` | `complete`, `sensor_missing`, `reference_missing` or `both_missing` |
| `reported_unit` | Null for all records; unit is not stated in annex headings |
| `unit_status` | Constant `not_stated_in_annex` |
| `quarantine_flags` | Semicolon-separated unresolved conditions for transfer/validation uses. Every row retains `physical_device_identity_unresolved` and `exact_cohort_mapping_unverified`; `unit_unresolved` remains only for PM1. Date/station/clock and source-summary conflicts are retained where relevant |
| `source_row_text` | Source row with PDF whitespace collapsed; numeric order and split date/time order retained. This aids review but is not a byte-for-byte PDF text representation |
| `effective_unit` | Author-confirmed `ug/m3` for NO2, NO, O3, SO2, PM10 and PM2.5; `mg/m3` for CO; null for PM1. Applies to both numerical columns. No numerical conversion was made |
| `effective_unit_basis` | `author_confirmation` for the seven confirmed pollutants; `not_confirmed_PM1_outside_original_pollutant_corpus` for PM1 |
| `author_annotation_id` | `H2022-A1`, resolving to the dated provenance and scope in `docs/author_annotations.json` |
| `analysis_status` | `descriptive_agreement_only` for confirmed units; `numerical_summary_only_unit_unconfirmed` for PM1. Does not authorize a new conformity or exact-cohort attribution claim |

`source_row` and `page_row` identify table rows rather than PDF line numbers. The content hash identifies the exact PDF version, and `pdf_page` supplies an unambiguous locator even where printed annex numbering is duplicated.

## Summary fields

`complete_pairs` counts rows with both numeric cells. Missing sensor and reference counts overlap for rows missing both. `diagnostic_grid_unlisted_points` counts nominal hourly/minute instants not printed between the series' minimum and maximum dates; it must not be reported as campaign data completeness. `unique_timestamp_interval_seconds` records consecutive distinct timestamp spacings. `exact_equal_pairs` describes literal equality only. Neither equal pairs nor negative values are removed or assigned causal interpretations.

The PDF verification output checks literal transcription. The author-annotation verification separately checks the protected-source-column fingerprint, unchanged null source-unit/identity fields and annotated-unit counts. Neither authenticates the source's signature, certifies the measurement method, infers a coverage factor or establishes raw logging resolution.

## Analysis outputs

`paired_agreement_metrics.csv` uses only complete source pairs. `n` is the number of rows, not the number of statistically independent samples. Bias is sensor minus reference. MAE, RMSE, intercept and the numerical ranges inherit `effective_unit` when confirmed. PM1's corresponding fields are arithmetic on the unconfirmed numerical scale, without an assigned physical unit. Pearson r is dimensionless; slope is a ratio of the printed sensor/reference scales and is dimensionless only where a common physical unit is established.

`ols_slope_sensor_on_reference` and `ols_intercept_sensor_on_reference` describe the projection of sensor onto reference with an intercept. They are not applied to modify readings. `regression_direction_diagnostics.csv` supplies the reverse projection for source-table interpretation; reversing the OLS direction is not equivalent to taking the reciprocal of the forward slope. `largest_absolute_errors.csv` identifies retained observations with large printed discrepancies, not confirmed data errors.
