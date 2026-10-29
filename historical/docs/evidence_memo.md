# Historical evidence memo after author confirmation

## Scope and provenance

The author statements “I confirm they are related use them” and “Confirmed the units are the same” are retained verbatim in `docs/author_annotations.json`, annotation H2022-A1. They authorize use of the related historical reports and establish the operational measurement-unit interpretation. They do not establish a physical serial mapping, exact cohort mapping to the 171 metrics, corrected dates, coverage factors or corrected uncertainty summaries. PM1 lies outside the original pollutant corpus and is not assigned a physical unit.

All 18 protected source columns are unchanged. Their canonical SHA-256 remains `b7dca4c3eca7bc555db30f73c8e8c88040a7f72ef89f19e160ed0687d7650b06`. Reported units remain null; effective units and their author-confirmation basis are separate fields. No numeric conversion, calibration, new timestamp join, lag adjustment, imputation or outlier exclusion was applied.

## Compact results for the paper

Bias means sensor minus reference. Bias, MAE and RMSE use the unit shown. These are equal-weight complete-pair summaries of the printed rows, not estimates of conformity or expanded measurement uncertainty.

| Pollutant | Complete pairs | Unit basis | Bias | MAE | RMSE | Pearson r |
|---|---:|---|---:|---:|---:|---:|
| NO2 | 800 | Author-confirmed µg/m³ | 9.324 | 12.131 | 14.859 | 0.895 |
| NO | 788 | Author-confirmed µg/m³ | -0.114 | 4.302 | 6.446 | 0.899 |
| O3 | 774 | Author-confirmed µg/m³ | 3.963 | 8.451 | 11.371 | 0.896 |
| SO2 | 535 | Author-confirmed µg/m³ | -0.071 | 0.150 | 0.387 | 0.780 |
| CO | 29 | Author-confirmed mg/m³ | -0.048 | 0.090 | 0.095 | 0.900 |
| PM10 | 2,222 | Author-confirmed µg/m³ | 1.158 | 6.481 | 10.522 | 0.957 |
| PM2.5 | 2,222 | Author-confirmed µg/m³ | -3.964 | 4.723 | 6.818 | 0.859 |
| PM1 | 4,798 | Unconfirmed; r only | — | — | — | 0.957 |

Seven confirmed pollutants provide **7,370 complete pairs**. The complete historical preparation contains **12,610 rows and 12,168 complete pairs**, including **4,798 complete PM1 pairs**. PM1 has 442 incomplete rows, comprising 69 sensor-only missing, 367 reference-only missing and six both-missing rows. No missing row was deleted from the recovered CSVs.

### PM1 arithmetic on an unconfirmed numerical scale

The separate PM1 numerical results are bias −13.9477699041, MAE 13.9928303460, RMSE 15.3684370662, Pearson r 0.9565153497, OLS sensor-on-reference slope 0.7530495786 and intercept −5.0660780756. No physical unit is assigned to bias, MAE, RMSE or intercept. The slope is a ratio of the printed scales, not an asserted dimensionless physical calibration coefficient. These values should not appear under a µg/m³ table heading.

## Interpretation and limits

- Association and agreement answer different questions. NO2 has r≈0.895 while its observed mean difference is +9.324 µg/m³ and RMSE 14.859 µg/m³. PM2.5 has an observed mean difference of −3.964 µg/m³. These are descriptive differences in the retained pairs, not inferred systematic errors for every deployment.
- SO2 reference and sensor tables each contain only the values 3, 4 and 5 µg/m³. Of 535 pairs, 455 are equal. The narrow, coarsely tabulated range limits generalization despite MAE 0.150 µg/m³.
- CO has only 29 pairs and three distinct reference values, 0.3, 0.4 and 0.5 mg/m³. Its r≈0.900 does not establish performance across a broader concentration range. The source also conflicts over the year, and its clock/timezone interpretation remains unresolved.
- Serial dependence and unequal time coverage remain. Counts represent printed observations, not independent samples. PM1 complete-case results do not characterize the unknown missing-data mechanism. No p-values, confidence intervals or conformity labels are supplied.
- The printed pairs are accepted as documentary pairings only. No independently verified co-location, clock synchronization, lag or equivalence of reference/sensor averaging intervals is asserted. Annex dates are used exactly as printed.
- Current-paper mappings remain unverified. A source relationship confirmed by the author does not identify which historical row or physical sensor generated each of the 171 metrics or resolve the later campaign dates.

## Regression direction

The supplemental OLS fit is explicitly `sensor = intercept + slope × reference`. Each series has nonzero reference variance, making the descriptive fit identifiable. OLS here is an algebraic description of the observed values; it does not assume a metrologically error-free reference for calibration or change any reading.

Source page 29 does not establish regression orientation in its summary heading. Most listed slopes are closer to the reverse regression, `reference = intercept + slope × sensor`. For example, PM10 gives a forward slope 1.067916 and reverse slope 0.857080; the source reports 0.86. CO gives 2.455696 forward and 0.329932 reverse; the source reports 0.33. The NO source slope 0.98 matches neither the forward 0.726264 nor reverse 1.112362 fit. NO2 and PM1 are near reverse fits but do not exactly reproduce at the stated rounding. Do not diagnose all forward/source slope differences as reproduction failures, or claim exact reverse-fit reproduction. Full values are in `data/regression_direction_diagnostics.csv`.

Recomputed Pearson coefficients round to the source page-29 correlation coefficients for all eight pollutants. This is evidence of consistency with the historical annex summary, not evidence of a link to the current 171-record cohort.

## Large differences retained for review

The following are large printed differences, not observations proven to be invalid. All remain in the calculations. The full three-per-series list is `data/largest_absolute_errors.csv`.

| Series | Literal timestamp | Sensor | Reference | Sensor − reference | Unit | Source locator |
|---|---|---:|---:|---:|---|---|
| NO2 | 2021-12-14 21:00:00+00:00 | 94.79083316 | 159 | -64.209 | µg/m³ | PDF p. 82, series row 619 |
| O3 | 2021-12-16 13:00:00+00:00 | 60.14428602 | 2 | 58.144 | µg/m³ | PDF p. 213, series row 642 |
| PM10 | 2022-03-15 15:00:00 | 212.5 | 132 | 80.500 | µg/m³ | PDF p. 364, series row 1338 |
| PM2.5 | 2022-01-29 23:00:00 | 3.5 | 36 | -32.500 | µg/m³ | PDF p. 456, series row 414 |
| PM1 | 2022-01-17 07:18:00+00:00 | 7 | 104.1 | -97.100 | unconfirmed numerical scale | PDF p. 626, series row 439 |

The largest PM1 difference is followed by missing reference cells in the source. Neither the missingness cause nor a physical mechanism is inferred. The PDF transcription checks establish that the values are printed this way.

## Remaining source discrepancies

NO2 body page 19 versus annex pages 30–98, SO2 body page 25 versus annex pages 224–267, and CO body page 27 versus annex pages 268–270 retain conflicting dates. The NO2 station differs between body pages 10 and 19. Source uncertainty percentages conflict between pollutant tables and page 29 for PM10, NO2 and NO; the SO2 R-squared also conflicts. The author confirmation did not correct these values. PM1 text on pages 5 and 11 refers to `ug/m2`, which remains unresolved.

## Verification and reproduction

The independent PDF-word check matches all 12,610 timestamps and printed numeric-cell sequences, with zero unmatched rows. Annotation verification confirms unchanged protected source columns and null reported-unit/identity fields. A separate 50-digit decimal implementation using raw-moment formulas checks all 48 numerical metrics against the centred binary-float analysis; the maximum absolute difference is approximately 3.13×10⁻¹⁵, within the 10⁻¹⁰ relative-or-absolute tolerance. Pollutant-specific CSVs also match the combined file exactly.

Reproduce the pipeline using the commands in the package README. `data/annotation_verification.json`, `data/analysis_verification.json` and `data/verification.json` capture the checks. Source hashes and all package file hashes are provided.

## Suggested manuscript wording

> Following author confirmation that the recovered historical reports are related to the study and use the same measurement units, we performed a separate descriptive comparison of their tabulated sensor/reference pairs. The seven pollutants with confirmed units yielded 7,370 complete pairs; PM1 contributed 4,798 additional complete pairs on an unconfirmed numerical scale and is reported separately. We preserved the original values and timestamps and calculated unweighted bias, MAE, RMSE and Pearson correlation from the printed pairings. Unit annotations retain their author-confirmation provenance. Physical serial mapping, exact cohort linkage to the 171 metrics, and the documented date and source-summary discrepancies remain unresolved, so these comparisons are not interpreted as a new conformity assessment or a reconstruction of the current campaign uncertainty budgets.

## Stable metadata keys for integration

- Package `analysis_status`: `descriptive_comparison_author_units_with_unresolved_provenance`.
- Relationship status: `author_confirmed_related_reports`.
- Exact cohort mapping: `unverified`; physical serial mapping: `not_provided`.
- Confirmed-unit row status: `descriptive_agreement_only`.
- PM1 row status: `numerical_summary_only_unit_unconfirmed`.
- Author annotation file: `docs/author_annotations.json`; ID: `H2022-A1`.
- Effective units: `ug/m3` for NO2, NO, O3, SO2, PM10 and PM2.5; `mg/m3` for CO; null for PM1.
- The reported unit, device identity and reference identity remain null in every recovered row.
