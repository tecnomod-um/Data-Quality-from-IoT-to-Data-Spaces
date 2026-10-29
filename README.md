# Supplement S1: data quality reproducibility
This supplement contains the executed local checks and captured results,
corrected evidence encodings, a historical report-table secondary analysis,
a complete conference-author-manuscript comparison, the declared Spanish
regulatory interpretation, published Toolbox capability evidence and an
integration preparation. The Toolbox runner and alternative Orion-LD recipe
have not been executed on a real broker in the captured study.

## Reproduce the completed checks

Use Python 3.12 and an isolated environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python run_validation.py --input source/cen17660_evidence_input.json --output rerun
```

The supplied `results/` directory preserves the executed revision run. A rerun
goes into `rerun/`; its numerical benchmark timings will vary with the machine
and load. No network is needed after installing dependencies. All JSON-LD
contexts used by the completed tests are embedded and also supplied separately.
The `https://example.org/dq-profile#` IRIs identify this proposed experimental
vocabulary; they are not a claim of official Smart Data Models adoption and are
never fetched by the completed tests.

## Input provenance and corrections

`source/cen17660_evidence_input.json` is an anonymized transcription of the 171
records supplied with the manuscript. Device codes D1--D3 and all metric values,
units, supplied limits, reported results, and pollutant-specific contexts are
preserved. The evaluator name is replaced by Laboratory L1. The frozen `evidenceSource` wording records the reconstruction-stage state
("original report unavailable in this package"). Related historical reports have
since been recovered and their relationship and shared units author-confirmed;
the exact document/page-to-assertion and campaign link remains unestablished.
`source/provenance_update_2026-10-28.json` records this update without rewriting
the hashed input or the captured results. Its statement about unavailable
original evidence is therefore scoped to authenticated, matching source evidence
for each assertion. The historical paired analysis is supplied separately; it
does not silently overwrite the 171 numerical records or their dates.

The source had only 156 distinct identifiers for 171 records. Twelve identifier
values were reused for different controlled-concentration relative-error
measurements. The correction appends a deterministic context hash suffix to
the 27 records affected by those collisions, producing 171 distinct assessment
identifiers. `data/identifier_mapping.json` provides a full source/context to
revised-identifier mapping. No metric value was altered.

Between-sensor uncertainty is a group statistic. Its 21 supplied encodings
represent seven pollutant/group values repeated under the three device tags.
Their revised target is SensorGroup D1--D3; the original device tag remains as
transcription metadata. They are not 21 independent uncertainty estimates.

`data/normalized_evidence.jsonld` supplies explicit NGSI-LD Property and
Relationship wrappers, complete local JSON-LD term definitions, target links,
typed metric values, and the integrity status `source-unverified`. Every
`evidenceHash` is a real SHA-256 digest of the corresponding anonymized supplied
record, under the byte serialization contract in `canonical_bytes`. These
digests protect the distributed derivative. They are **not** hashes of the
original signed laboratory reports and do not authenticate a laboratory.

The exact-byte contract sorts object keys, uses compact ASCII JSON, forbids NaN
and infinity, and uses Python's JSON number serialization. It is a specified
implementation contract, not a general RFC 8785 or RDF canonicalization claim.

## Completed validation and adversarial checks

- All 171 normalized entities passed the application JSON Schema. All 171
  reported pass decisions agree with their supplied thresholds. This is a
  consistency check on transcribed reports, not an independent estimate of
  sensor accuracy or an empirical 100% detection rate.
- Eight deliberately malformed entities were rejected: missing metric code,
  nonnumeric metric, invalid result, missing target, malformed hash, an
  unjustified source-verification status, malformed target URI, and absent
  threshold.
- The normalized JSON-LD expanded to 10,557 RDF triples, with explicit checks
  that all 171 entity identifiers, metric values, and target links survive.
  The separate DQV,
  PROV-O, and DCAT export contains 2,273 triples. Its JSON-LD/RDF round trip is
  isomorphic. It passed the supplied SHACL application shapes, while removal
  of a provenance link was rejected. This tests a concrete export with
  general RDF tooling; it does not certify complete W3C ontology conformance
  or interoperability with every broker/catalogue.
- The included SPARQL query identifies the two expanded-uncertainty assertions
  with threshold utilisation above 0.90. These are O3/D1 and NO/D1.
- Twelve deterministic runtime cases exercise a declared synthetic policy.
  One healthy case is accepted and eleven adverse cases are quarantined.
  These exercise code paths, not estimated error rates. The adverse cases
  cover staleness, packet loss, schema failure, hardware failure, a statistical
  outlier, expired calibration, changed firmware, mismatched unit, mismatched
  site, missing source evidence, and altered evidence.
- A test-key Ed25519 signature verifies the exact message bytes and rejects an
  altered message. The key is deliberately public and deterministic, supplied
  only as a reproducible test fixture. It identifies no real evaluator,
  organization, instrument, or certificate.

The synthetic runtime score is
`0.5 * completeness + 0.3 * freshness + 0.2 * schema`, where completeness is
received unique valid slots / 60 and
`freshness = exp(-max(0, age_seconds - 60) / 60)`.
The healthy fixture has 58/60 slots, age 7 s and schema score 1, giving
0.9833333333. Acceptance additionally requires completeness at least 0.9,
age at most 120 s and nonnegative, schema score 1, current calibration,
matching unit/firmware/site, verified test-fixture integrity, healthy hardware,
no flagged outlier, an assumed authorization Boolean, and aggregate score at
least 0.9. The authorization fixture does not exercise TLS, identity or policy
infrastructure. Unknown evidence fails
closed. These are explicit illustrative engineering choices, not standards
requirements or statistically optimized parameters.

The outlier test creates 60 values `40 + 0.2*sin(i/5)` and replaces index 30 by
1000. Its detector flags absolute deviations exceeding
`6 * 1.4826 * median absolute deviation`; only index 30 is detected. The chosen
multiplier illustrates an incident path and has not been calibrated for a
real sensor population.

## Completed local overhead experiment

The workload represents 3,600 synthetic observations at 1 Hz, processed as an
in-memory archive. It does **not** wait for an hour or replay observations into
a broker. Seven runs of each mode are interleaved after a 60-observation warmup.
All modes count one shared context per archive. The tested machine reported
Python 3.12.14, Linux x86-64, an AMD EPYC 9V74 CPU model and nine available
logical CPUs; only one Python process was used in a shared execution environment.

| Mode | Assessment entities | Serialized component bytes | Median local processing time | Range |
| --- | ---: | ---: | ---: | ---: |
| Observation baseline | 0 | 966214 | 13.043 ms | 12.889--13.429 ms |
| Assessment and signature per observation | 3600 | 5834797 | 194.363 ms | 188.539--230.133 ms |
| Assessment and signature per 60-second window | 60 | 1815717 | 26.683 ms | 25.143--27.518 ms |

The measured path includes deterministic JSON serialization, incremental
SHA-256, and Ed25519 signing with the public test key. All observation values
are retained. Each assessment covers its window's ordered serialized
observations. Windowing reduces assessment/hash/signature counts by a factor
of 60 and total serialized component bytes by 68.88% relative to one assessment
per observation for this encoding. It still uses 1.879 times the bytes of the
observation-only baseline. Byte totals include hexadecimal signatures but not
HTTP headers, protocol framing, database indexes, compression, storage engine
overheads, or subscription fan-out.

The timed path excludes policy-gate evaluation, signature verification, source-value generation, parsing and I/O. Component byte totals are an analytical sum, not an emitted complete archive container or HTTP body.

These are local processing measurements, not broker latency, throughput,
persisted storage measurements, or end-to-end sensor-to-decision latency.
Window quality is computed after window closure and attached retrospectively
in this archive experiment. In an online deployment, a 60-second window adds
up to 60 seconds before final-window evidence is available. Applications
requiring quicker decisions need provisional flags and event-triggered fault
assessments, with the last closed assessment explicitly labelled as such.

## Separately recovered historical series

`historical/` contains 12,610 report-tabulated rows across eight pollutants,
including 12,168 complete sensor/reference pairs. The 442 incomplete PM1 rows
retain empty cells. Source-page provenance, literal dates/numeric strings,
parsed values, extraction scripts and an independent all-row PDF check are
included. No imputation or assumed unit conversion is performed.

The authors have confirmed that these reports are related to the study and
authorized their use. They also confirmed matching units for the seven shared
pollutants. The effective units are µg/m³ for NO2, NO, O3, SO2, PM10 and PM2.5,
and mg/m³ for CO. Source-table unit fields remain empty because the annex
headings did not print a unit; separate H2022-A1 metadata states the author
confirmation. PM1 has no counterpart in the original corpus and retains an
unconfirmed physical unit.

`historical/data/paired_agreement_metrics.csv` and its JSON companion report
executed mean sensor−reference difference, MAE, RMSE, Pearson r and descriptive
OLS summaries. Seven confirmed-unit series supply 7,370 complete pairs; PM1
adds 4,798 complete numerical pairs. Only pairwise missing rows are excluded;
there is no imputation, calibration correction, unit conversion or filtering.
PM1 dimensioned numbers remain report-scale diagnostics, not µg/m³ claims.

H2022 is the report cover date, not a common measurement year. Source dates,
physical/configuration identities, reference-station discrepancies and some
printed uncertainty/regression summaries remain unresolved. HS1–HS8 identify
annex series rather than established physical units. Related-report confirmation
does not identify the exact mapping to the 2024–2026 D1–D3 assertions. These
limits constrain certification and transfer claims but do not prevent the
transparent descriptive analysis now reported. See historical/README.md for
the exact commands, source-field digest, author annotations and verification.

## Conference baseline comparison

`conference_comparison.txt` records a complete author-version comparison with
source digest and section/table/equation locators. It distinguishes inherited
scoring recipes, gates, evidence fields, lifecycle, dual representation and
bundling from the revision's specification, correction and executed tests.
The identifying author PDF is kept outside this anonymous supplement, and
identity with the final publisher version is not asserted.

## Declared Spanish regulatory context

[`source/spanish_regulatory_context.json`](source/spanish_regulatory_context.json)
records the adopted interpretation under Spain's Real Decreto 102/2011,
including exact public sources and clause locators. The SO2 hourly reference
of 350 µg/m³ and the 25% indicative-measurement uncertainty objective give an
absolute uncertainty comparison bound of 87.5 µg/m³. The legal framework's
confidence basis does not establish the confidence level or coverage factor
of the transcribed expanded-uncertainty values.

NO=50 µg/m³ remains the supplied study criterion; it is not represented as a
Spanish legal limit for standalone NO or replaced by an NO2 proxy. The declared
interpretation does not authenticate original report-to-clause lineage,
establish a new conformity decision or alter any source value.

## Toolbox source, testbed access and prepared runner

The supplied application is
https://dpl-int.ldttoolbox.app/data/sources/list . The integration package is
aligned with the existing project
https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform . The pinned reference is
DP-1.0.0, resolved commit efc368c81a4e78d61615ba32b17c1c8dac35a174, whose local
and integration manifests pin Scorpio java-6.0.0. The APISIX source provides the
/cb/ gateway prefix; the corresponding runtime URL remains a source-derived
candidate, not a successfully verified API deployment.

[`integration/toolbox/capability_evidence.md`](integration/toolbox/capability_evidence.md)
and its JSON companion document the inspected Data Platform, Data Space Ready
and identity source revisions. The source register covers native broker and
temporal APIs, persistence, subscriptions, cross-store queries, authorization
and connector-specific discovery/policy/contract/transfer operations. TMF620
catalogue management for FIWARE-compatible connectors differs from EDC catalogue
discovery; full Simpl adapters remain an extension path. Published source and
load-test harnesses are evidence of implementation capabilities, not measured
performance of this quality profile. The accompanying five-stage measurement
protocol is explicitly prospective.

`integration/toolbox/README.md` documents the new primary integration path.
Its standard-library runner defaults to an offline plan and can perform a
bounded six-entity query/evidence/consumer exercise once the API is reachable
and the experimental tenant and roles are assigned. Open registration is
author-confirmed; the registration form was not reached from this environment.
Nine safety/failure-path tests pass using an explicitly offline transport
substitute. The preserved unauthenticated API observations returned HTTP 503
before sign-in; no registration form was reached. These diagnostics are
separate from the documented platform capabilities and captured local tests.
No successful live query, subscription, connector exchange or operational
benchmark is claimed for this study.

The study contribution is prepared for a new
`tests/reproducibility/data_quality/` directory and a companion documentation
guide in that existing project. It has not been pushed or published.
`integration/toolbox_reference.json` and the detailed source/access files keep
configuration evidence, intended execution and captured results distinct.

## Alternative Orion-LD recipe that was not executed

`integration/compose.yaml` and `integration/broker_smoke_test.py` are an
**ALTERNATIVE, unexecuted** two-broker recipe. They are not the Toolbox's actual
Scorpio configuration. The recipe pins Orion-LD 1.12.0 and describes two
broker/database pairs plus a local context server, with broker ports exposed
only on localhost. It is a separate starting point for a controlled experiment;
using the available Toolbox testbed instead requires its supplied replication
configuration and the applicable API/identity arrangements.

```bash
cd integration
docker compose up -d
# Check both brokers report healthy startup before executing the test.
python broker_smoke_test.py
docker compose down
```

The smoke test attempts to create one synthetic assessment and three
observations, filter by both a score and a passed gate, verify an exact-byte
test signature, and transfer the selected bundle from producer to consumer
broker. It writes results only when all assertions succeed. Any unsupported
query, context resolution problem, container incompatibility, or broker error
must be investigated and reported; the unexecuted recipe is not counted as a
successful experiment. Add authenticated identities, a real connector,
repeatable load generation, baseline/quality-aware query and subscription
benchmarks, and failure/recovery testing before making production or data-space
interoperability claims.

## Main files

`results/validation_summary.json` records the combined executed results and
dependency versions. `results/benchmark_raw.csv` preserves all 21 timing runs.
`results/scenario_results.json` records each decision, failed gate, and incident
identifier. The `schemas/`, `queries/`, `contexts/`, and `data/` directories hold
the corresponding application constraints and encodings.


## Additional manuscript examples

Run `python fusion_demo.py` to reproduce the four conditional fusion cases.
Run `python make_listing_example.py` to regenerate the complete synthetic Listing 1 observation, assessment, device fixture and exact hashed inputs. These runtime example files are separate from the 171 certificate-derived entities and their schema. Their qualification assumptions are synthetic, not transferred from the supplied device reports.
