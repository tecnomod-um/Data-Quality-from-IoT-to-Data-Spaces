# EU LDT Toolbox capability evidence and measurement mapping

Reviewed on 28 October 2026. This addendum supports reviewer items R2.2, R2.3 and R2.4. It documents concrete implementations in the official public Toolbox source, maps them to the proposed quality profile, and specifies the measurements needed to evaluate that profile. Source inspection establishes published implementation capability. The study's successful executions remain the separately captured local tests and analyses; its broker, subscription and governed connector transactions have not been executed successfully.

## Pinned source

| Component | Tag | Inspected commit |
|---|---|---|
| Data Platform | `DP-1.0.0` | `efc368c81a4e78d61615ba32b17c1c8dac35a174` |
| Data Space Ready | `DSR-1.0.0` | `e5bdd28ddaf38a4473b5187a88567d737a22fb8e` |
| Identity Management | `IM-1.0.0` | `7ee287e653cc70e76db18bf96b2974cd7560e585` |

These are inspected source revisions, not observations of the versions currently running on the public integration service. The companion JSON records the URL and SHA-256 digest of each inspected source file.

## Functional and verification matrix

| Published Toolbox component | Concrete published capability | Study mapping and verification boundary |
|---|---|---|
| Scorpio context broker | `java-6.0.0` deployment, current entities, native query and batch routes behind `/cb/*`. [S01–S06, S12–S13] | The prepared probe publishes linked quality entities, asks a native quality query and applies consumer evidence checks. Offline tests validate the runner; successful broker results are still needed. |
| Persistent context and temporal data | INT TimescaleDB `pg17-ts2.18-oss`, database `ngb`, logical WAL and `timescaledb-pvc`; separate temporal create/query/delete methods. [S03–S06] | Current state, retained history and linked assessments must be counted separately. Existing serialized component bytes do not measure database, index or WAL growth. |
| Subscriptions | Subscription CRUD plus HTTP/MQTT examples with selectors, watched attributes and throttling. [S07–S08] | Quality changes can be mapped to callbacks and reassessment. The supplied bounded probe has no subscription receiver or captured delivery measurement. |
| Queries across stores and replication | Trino catalogues for PostgreSQL, TimescaleDB, MongoDB, Hive/MinIO, Kafka and OpenAPI; example cross-store JOIN; Debezium/Kafka CDC workflow. [S09–S11] | These identify concrete data/evidence retrieval and replication paths. SQL across stores, CDC and governed cross-party exchange require distinct verification. |
| Identity and authorization | Keycloak identity component; APISIX OIDC and OPA tenant/group checks; consumer, producer and subscriptor roles. [S12–S14, S32] | Independent credentials and an assigned experimental tenant support producer/consumer tests. Registration availability is an author-confirmed policy; actual role assignment and request decisions must be recorded. |
| Data-space discovery and exchange | TMF620 catalogue management for `ngsi-ld`/`custom`; EDC/FDSC search; EDC/FIWARE policy dispatch; EDC catalogue discovery, negotiations and transfer/EDR services; FIWARE identity federation. [S15–S23] | These implementations provide a concrete integration path for a published evidence distribution and independent consumer. No study-specific catalogue, agreement or transfer trace is available. Connector operations differ; full Simpl adapters are an extension path. [S24] |

### Native API and role contract

The source-derived native prefix is `/cb/ngsi-ld/v1`; APISIX removes `/cb` before forwarding to Scorpio. Native requests select the tenant with `NGSILD-Tenant`. For a non-admin account, the group form is `/context-data/<tenant>/<role>`. Current and temporal entity reads admit `consumer`, `producer` or `admin`; writes and batch operations require `producer` or `admin`. Subscription management requires `subscriptor` or `admin`. These rules come from the pinned integration OPA configuration. [S12–S14]

The runner uses the native route with the supplied quality context. The inspected Python wrapper removes inline `@context` in `create_entity` before forwarding `application/json`; therefore wrapper and native-route behavior should not be treated as interchangeable. The native-query context must be retrievable by the broker, and its hash should be captured. [S04]

### Connector scope

The catalogue factory explicitly provides TMF620 catalogue management for `ngsi-ld` and `custom` connectors and rejects `edc` and `simpl` for that operation. Separate EDC catalogue discovery calls `/api/management/v3/catalog/request`; EDC negotiation methods use `/api/management/v3/contractnegotiations`. Transfer methods use `/api/management/v3/transferprocesses` and an EDR data-address endpoint. The transfer service validates the selected connector and agreement before invoking the adapter; it constructs HTTP PUSH/PULL and S3 destination forms. These are published code paths, not recorded transactions for this study. [S16, S19–S22]

The Simpl guide lists type recognition, verification and extension points, then explicitly requires full adapters and factory registration. Consequently, the paper should describe connector-specific support and avoid asserting complete interoperability with every connector type. [S24]

## What the public performance material supplies

The pinned Data Platform repository contains Locust workloads for current, batch, geographic and temporal operations, a query-oriented workload that includes subscription listing, a Trino `SHOW CATALOGS` workload, and CPU/memory aggregation code. Its Makefile generates CSV reports under `reports/performance`. The inspected files do not include the generated reports or the docker-stat inputs expected by the aggregation script. [S25–S29]

Data Space Ready also publishes a Locust suite and a performance guide. The guide explains generated HTML/CSV reports and proposes response-time/error targets; those targets are not achieved measurements. Some guide prose describes stress capabilities as planned while source contains stress scenarios, so source presence alone does not establish empirical validation of the suite. [S30–S31]

No published numerical result for this quality profile, or reusable captured output accompanying the inspected harnesses, was located in the scoped source and official-domain review. This does not assert that no Toolbox benchmark exists elsewhere. Existing upstream load settings, example responses and release notes cannot replace a matched evaluation of the proposed sub-properties, linked assessments, history and callbacks.

## Additional measurement protocol

**All parameters in this section specify future measurements. They are not additional results.** The protocol reuses the available synthetic workload and is separate from the executed local serialization/hash/signing experiment.

| Stage | Controlled comparison | Required capture |
|---|---|---|
| Workload | Same 3,600 measured observations, values, timestamps and quality cases in baseline, per-observation and 60-second-window evidence encodings. The proposed primary workload is one hour at 1 Hz, with seven repetitions per mode in interleaved order. Exclude 60 warm-up observations from each run. | Workload/configuration hashes, actual sensor count and achieved rate, image/resource/tenant/context/retention settings, operation counts and per-run raw records. Accelerated replay, if used, is reported separately. |
| Storage/history | Same effective retention, indexing and batching; clear the 60 warm-up observations and their assessments before each storage baseline. Measure current entities and historical instances separately; verify exactly 3,600 measured observation records. | Serialized bytes, database/table bytes, indexes and WAL as separate quantities; baseline/final counts; checkpoint/compaction timing and owned-record cleanup, distinguishing deletion from physical reclamation. |
| Query | Baseline: matched-ID selector only. Quality modes: native quality predicate plus matched-ID selector control, using the same expected IDs, returned attributes and cardinality/pagination/cache state. Report the practical unfiltered-versus-filtered case separately. | At least 100 timed requests per query per run after query warm-up; exact predicates and result-ID sets, response bytes, median/p95 with sample counts, errors and achieved rate; separate evidence-fetch/consumer-validation timing. |
| Subscriptions | Fixed selectors, fan-out, throttling, receiver and retry policy; sequence/correlation IDs; a separately authorized restart/recovery trial on a dedicated experimental deployment. | Expected qualifying updates, unique deliveries, duplicates, missing updates by a stated deadline, callback bytes and latency with clock-error accounting. |
| Two-party exchange | Independent producer/consumer processes and credentials; one supported DSR connector workflow; allowed and denied access, stale evidence and digest-mismatch cases. | Asset/offer/policy/agreement/transfer identifiers, sanitized role metadata, source/consumer hashes and explicit evidence-dependent decisions. |

The common acceptance mask is external fixture ground truth. Baseline records contain no quality sub-properties or assessments, so a quality predicate is not run on them. The two quality modes are compared with their own matched-ID controls under the same declared test policy.

The future broker fixture declares a versioned runtime vocabulary that maps the archive label `synthetic-valid` to `valid` for the corresponding eligible runtime case. Invalid and failed-gate cases follow the declared policy. This prospective mapping does not modify the archived fixture, captured results or their hashes. The 60 warm-up observations are excluded from measured record counts and timings, and their owned records are cleared before each storage baseline.

The current bounded runner compares three unfiltered entities with one quality-filtered entity. Its descriptive request timings would combine filtering and response-cardinality effects; they cannot isolate predicate overhead. A matched-result control is therefore essential. Seven repetitions are seven independent run summaries, not a sufficient per-request sample count by themselves for a stable tail-latency estimate.

The source contains explicit temporal writes and reads, while the platform README describes historical data derived from acquisition changes. A replication must record its effective automatic-history/retention configuration and verify the number of stored samples; it must not infer retained history from a latest-value query. [S01, S04–S05]

For subscription latency, either use a common measurement clock or record source/receiver clock synchronization and its uncertainty. A callback HTTP success code does not prove downstream processing success. Restart tests belong in a dedicated authorized deployment; the shared public service must not be restarted for this study.

## Reviewer response mapping

**R2.2:** The revised architecture can now identify published broker, persistence, catalogue/connector and authorization implementations, in addition to the locally tested consumer logic and prepared native-broker probe. Source inspection strengthens implementation specificity; successful profile transactions remain outside the captured evidence.

**R2.3:** The native quality-query route and tenant roles identify a concrete broker integration, and DSR's actual discovery, negotiation and transfer methods identify a concrete two-party path. Prepared logic, code adapters and two clients sharing a broker must not be described as an observed governed exchange.

**R2.4:** The existing numerical component-byte and assembly/hash/signing results remain valid within their stated local scope. Persistent storage, native query and subscription overhead require the controlled measurements above. Published load-test harnesses supply reusable methods, not substitute results.

## Runtime and release boundary

Both existing reachability records are preserved. The follow-up record reports an unauthenticated HTTP 503 at `2026-10-28T06:24:59.870123+00:00`, with the upstream timeout body. Its 5.013-second elapsed time is a reachability observation, not a broker benchmark. No fresh live request was made for this addendum. Author-confirmed open registration remains recorded separately; it does not conflict with the observed connection failure from this environment.

This addendum does not change the study flags for actual broker, connector or municipal deployment execution. It does not assert a public deposit, repository merge or tagged study release.

## Source register

All links below refer to the exact inspected commit. The companion JSON contains file hashes and a machine-readable six-row capability matrix, reviewer mapping, role contract and five-stage measurement protocol.

- **S01** — [DP: README.md](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/README.md). Concepts: acquisition, historical data, storage, query and replication.
- **S02** — [DP: infrastructure/local/base/1-ContextData/Scorpio/deployment.yml](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/infrastructure/local/base/1-ContextData/Scorpio/deployment.yml). Scorpio container image and DBHOST.
- **S03** — [DP: infrastructure/int/1-DataContext/TimeScaleDB/deployment.yml](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/infrastructure/int/1-DataContext/TimeScaleDB/deployment.yml). TimescaleDB image, database ngb and persistent volume claim.
- **S04** — [DP: backend-py/src/services/context_brokering_clients/scorpio_broker_client.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/backend-py/src/services/context_brokering_clients/scorpio_broker_client.py). Native entity, temporal and subscription URLs; current and temporal methods.
- **S05** — [DP: backend-py/src/controllers/context/temporals.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/backend-py/src/controllers/context/temporals.py). TemporalParams and explicit create/query/delete temporal routes.
- **S06** — [DP: backend-py/src/controllers/context/entity_operations.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/backend-py/src/controllers/context/entity_operations.py). Batch update and delete controller routes.
- **S07** — [DP: documentation/guides/CONTEXT_DATA_SUBSCRIPTION_SAMPLE.md](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/documentation/guides/CONTEXT_DATA_SUBSCRIPTION_SAMPLE.md). HTTP and MQTT notification examples with watched attributes.
- **S08** — [DP: backend-py/src/controllers/context/subscriptions.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/backend-py/src/controllers/context/subscriptions.py). Subscription create/list/get/patch/delete controller.
- **S09** — [DP: documentation/guides/DATA_QUERY_CONFIG.md](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/documentation/guides/DATA_QUERY_CONFIG.md). Trino catalogue configuration for heterogeneous sources.
- **S10** — [DP: documentation/guides/DATA_QUERY_SAMPLE.md](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/documentation/guides/DATA_QUERY_SAMPLE.md). Illustrative cross-catalogue JOIN and Trino /v1/statement.
- **S11** — [DP: documentation/guides/DATA_REPLICATION.md](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/documentation/guides/DATA_REPLICATION.md). Debezium/Kafka CDC and replication API workflow.
- **S12** — [DP: infrastructure/int/5-Proxy/APISIX/configMap.yml](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/infrastructure/int/5-Proxy/APISIX/configMap.yml). /cb/* reverse proxy, OIDC and OPA.
- **S13** — [DP: infrastructure/int/5-Proxy/OPA/configMap.yml](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/infrastructure/int/5-Proxy/OPA/configMap.yml). Tenant-scoped roles for current, temporal, batch and subscription endpoints.
- **S14** — [DP: documentation/guides/CONTEXT_DATA_AUTHORIZATION.md](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/documentation/guides/CONTEXT_DATA_AUTHORIZATION.md). Context-data groups and minimum role distinctions.
- **S15** — [DSR: README.md](https://code.europa.eu/ldt-toolbox/eu_ldt_data_space_ready/-/blob/e5bdd28ddaf38a4473b5187a88567d737a22fb8e/README.md). Data Space Ready identity, management and governance components.
- **S16** — [DSR: backend-py/src/services/adapters/catalogue_adapter_factory.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_space_ready/-/blob/e5bdd28ddaf38a4473b5187a88567d737a22fb8e/backend-py/src/services/adapters/catalogue_adapter_factory.py). TMF620 catalogue management for ngsi-ld/custom; EDC/SIMPL rejected for this operation.
- **S17** — [DSR: backend-py/src/services/adapters/search_adapter_factory.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_space_ready/-/blob/e5bdd28ddaf38a4473b5187a88567d737a22fb8e/backend-py/src/services/adapters/search_adapter_factory.py). EDC and FDSC search dispatch.
- **S18** — [DSR: backend-py/src/services/adapters/policy_adapter_factory.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_space_ready/-/blob/e5bdd28ddaf38a4473b5187a88567d737a22fb8e/backend-py/src/services/adapters/policy_adapter_factory.py). EDC and FIWARE policy dispatch.
- **S19** — [DSR: backend-py/src/services/adapters/edc_catalog_adapter.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_space_ready/-/blob/e5bdd28ddaf38a4473b5187a88567d737a22fb8e/backend-py/src/services/adapters/edc_catalog_adapter.py). EDC catalog/request discovery and contract-offer retrieval.
- **S20** — [DSR: backend-py/src/services/adapters/edc_contract_negotiation_adapter.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_space_ready/-/blob/e5bdd28ddaf38a4473b5187a88567d737a22fb8e/backend-py/src/services/adapters/edc_contract_negotiation_adapter.py). EDC negotiation initiation, lookup, acceptance and status.
- **S21** — [DSR: backend-py/src/services/adapters/edc_transfer_adapter.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_space_ready/-/blob/e5bdd28ddaf38a4473b5187a88567d737a22fb8e/backend-py/src/services/adapters/edc_transfer_adapter.py). EDC transfer-process and EDR endpoints; HTTP PUSH/PULL and S3 destination construction.
- **S22** — [DSR: backend-py/src/services/contract_management/transfer_service.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_space_ready/-/blob/e5bdd28ddaf38a4473b5187a88567d737a22fb8e/backend-py/src/services/contract_management/transfer_service.py). Connector/contract validation followed by EDC transfer adapter.
- **S23** — [DSR: documentation/guides/FIWARE_CONNECTOR_INTEGRATION_GUIDE.md](https://code.europa.eu/ldt-toolbox/eu_ldt_data_space_ready/-/blob/e5bdd28ddaf38a4473b5187a88567d737a22fb8e/documentation/guides/FIWARE_CONNECTOR_INTEGRATION_GUIDE.md). FIWARE identity federation, token exchange, connector registration and credential issuance.
- **S24** — [DSR: documentation/guides/SIMPL_CONNECTOR_SUPPORT.md](https://code.europa.eu/ldt-toolbox/eu_ldt_data_space_ready/-/blob/e5bdd28ddaf38a4473b5187a88567d737a22fb8e/documentation/guides/SIMPL_CONNECTOR_SUPPORT.md). SIMPL type/verification readiness; full adapters and factory registration remain implementation steps.
- **S25** — [DP: tests/performance/load_tests.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/tests/performance/load_tests.py). Locust current, batch, geographic and temporal operation workload.
- **S26** — [DP: tests/performance/stress_tests.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/tests/performance/stress_tests.py). Locust query, attribute, type, subscription-list and temporal workload.
- **S27** — [DP: tests/performance/trino_load_test.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/tests/performance/trino_load_test.py). Trino SHOW CATALOGS workload.
- **S28** — [DP: tests/performance/calculate_averages.py](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/tests/performance/calculate_averages.py). Average CPU/memory calculation from generated docker-stat CSVs.
- **S29** — [DP: Makefile](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/Makefile). performance-tests-scorpio and performance-tests-trino generate CSV reports.
- **S30** — [DSR: documentation/guides/STRESS_TESTING.md](https://code.europa.eu/ldt-toolbox/eu_ldt_data_space_ready/-/blob/e5bdd28ddaf38a4473b5187a88567d737a22fb8e/documentation/guides/STRESS_TESTING.md). Performance methodology, expected reports and acceptance targets; not captured measurements.
- **S31** — [DSR: tests/performance/Makefile](https://code.europa.eu/ldt-toolbox/eu_ldt_data_space_ready/-/blob/e5bdd28ddaf38a4473b5187a88567d737a22fb8e/tests/performance/Makefile). Locust load/stress harness entry points and report generation.
- **S32** — [IM: README.md](https://code.europa.eu/ldt-toolbox/eu_ldt_identity_management/-/blob/7ee287e653cc70e76db18bf96b2974cd7560e585/README.md). Keycloak-based identity and access-management component.
