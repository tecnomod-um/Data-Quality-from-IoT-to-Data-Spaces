# EU LDT Toolbox replication harness

This proposed harness targets the EU LDT Data Platform's authenticated NGSI-LD
gateway. It provides an offline plan, one bounded read-only reachability probe,
and a small synthetic create/query/consumer-decision/cleanup exercise. It has
**not executed a quality-profile experiment on the integration testbed**.
The completed manuscript results remain in the supplement's existing `results/`
directory and are not modified by this harness.

## Source reference and observed access

The existing source project is
[ldt-toolbox/eu_ldt_data_platform](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform),
public project ID 1917. The inspected release tag is `DP-1.0.0`, resolving to
commit `efc368c81a4e78d61615ba32b17c1c8dac35a174` dated 22 July 2026.
Both its local and integration manifests pin
`public.ecr.aws/scorpiobroker/all-in-one-runner:java-6.0.0`.

The [pinned integration APISIX configuration](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/infrastructure/int/5-Proxy/APISIX/configMap.yml)
routes `/cb/*` to `context-brokering:9090`, removes the `/cb` prefix, requires
bearer OIDC authentication, and applies the context-brokering OPA policy.
Therefore `/cb/ngsi-ld/v1` is the source-supported gateway API prefix.
The hostname remains a deployment variable in the pinned source.

The author supplied
[the integration frontend](https://dpl-int.ldttoolbox.app/data/sources/list)
and [the LDT identity realm](https://im-int.ldttoolbox.app/realms/LDT/).
Combining the supplied frontend origin with the pinned gateway prefix gives
`https://dpl-int.ldttoolbox.app/cb/ngsi-ld/v1` as a **source-derived candidate
API base**. The frontend's `/data/sources/list` path is a UI route.

The author confirms that the integration environment is open and anyone can
register. This statement is recorded separately from what the revision
environment could reach. Two bounded unauthenticated GETs on 28 October 2026
returned HTTP 503 and an upstream connection-timeout message before any sign-in
or data operation. The original sanitized record remains in
`access_observation.json`; the follow-up at 06:24:59 UTC is preserved in
`followup_access_observation.json`. Their durations of 5.011 and 5.013 seconds
are reachability observations, not broker latency. No credentials were
supplied, no registration or authentication was completed, no entity was
created, and no quality query was executed. These observations concern this
execution environment and do not establish whether other users can currently
register. `source_reference.json` records the exact pinned source paths and
SHA-256 digests. Source inspection does not identify the running testbed image.

## Inputs needed for an actual run

| Input | Purpose and source boundary |
| --- | --- |
| Reachable, confirmed API base | The candidate above is configured, but its application route has not responded successfully. Use the deployed gateway URL confirmed by the operator. |
| Assigned context-data tenant | Set `LDT_NGSILD_TENANT` to an existing scope approved for six synthetic entities. The pinned scope-name pattern is lowercase letters, digits and underscores. The harness does not create a tenant. |
| Short-lived producer access token | Set `LDT_ACCESS_TOKEN`. The token must be accepted by the gateway and permit entity GET, POST and DELETE in that tenant. |
| Optional consumer token | Set `LDT_CONSUMER_ACCESS_TOKEN` to exercise reads with a separately supplied credential. Otherwise the producer credential also performs reads. Different token values do not by themselves establish different people or organizations. |
| Hosted experimental context | Set `LDT_CONTEXT_URL` to an HTTPS URL serving this directory's `context.jsonld`. It must be reachable by both the client and broker. The harness checks the document equals the bundled context and sends no bearer token to the context host. |
| Actual configuration record | Capture the running Data Platform revision, broker image/digest, tenant, gateway/identity policy version and relevant resource limits before interpreting a run as a reproducible experiment. The reference tag is not a substitute for this information. |

The [pinned OPA policy](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/infrastructure/int/5-Proxy/OPA/configMap.yml)
requires a `resource_access` entry for the configured OAuth2 client. For a
non-admin identity, tenant membership is represented as
`/context-data/<tenant>/producer` for entity reads/writes and
`/context-data/<tenant>/consumer` for reads. The client-role mapping includes
`User`, `Technician` and `Admin`; the operator must confirm the deployed mapping.
A role name alone is not a substitute for the tenant group required by this
policy. Subscriptions require `subscriptor` or `admin`, but this harness creates
no subscriptions. The health endpoint is admin-only in the pinned policy and
is not used as a prerequisite for ordinary consumer access.

Once the application is reachable from the replication environment, use its
registration/sign-in flow to obtain an account. Public registration does not
by itself establish the tenant-specific producer permissions needed for this
experiment. Confirm the assigned scope and permitted operations before running
the six-entity exercise; the harness does not grant roles or create accounts.

The [integration configuration](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/infrastructure/int/configMap.yml)
sets gateway client `tool6-backend` and public client `tool6`, while the OAuth2
client ID used by the OPA template remains a deployment placeholder. Do not
guess the deployed audience or copy a demonstration credential from a guide.
Obtain the token through the operator's approved OIDC flow. This runner accepts
the resulting token; it does not acquire, refresh, print or persist it. It sends
only `Authorization: Bearer ...`; it does not fabricate the gateway's internal
claims headers.

## Run the offline plan first

Python 3.12 is sufficient; the runner uses only the standard library. From this
directory:

```bash
python probe.py plan --output ../../rerun/toolbox-plan
python -m unittest discover -s tests -v
```

`plan` performs no network requests. It emits the six proposed entities, exact
fixture inputs, query expression and an explicit planned status. The tests use
an in-memory HTTP test double and label its transport `offline_test_double`.
Neither the plan nor these tests constitute broker validation. Output
directories must be new, so reruns cannot replace earlier captured results.

`config.example.json` contains non-secret settings. Environment variables can
override `api_base_url`, `tenant`, `context_url` and `ca_bundle` through
`LDT_API_BASE_URL`, `LDT_NGSILD_TENANT`, `LDT_CONTEXT_URL` and `LDT_CA_BUNDLE`.
`env.example` lists the variables without credentials. Keep actual tokens in
the execution environment, outside configuration files and version control.
TLS certificate verification remains enabled. Redirects are refused and
tokens are never sent to the context-document host.

## Read-only probe and actual measurement mode

Once the service is reachable from the replication environment, a single
read-only check is:

```bash
python probe.py probe --output ../../rerun/toolbox-reachability
```

It queries a newly generated nonexistent identifier with `limit=1`. It does not
list tenant data, change endpoints automatically, or infer permission from an
HTTP response. HTTP 401, 403 and 503 are captured as their observed outcomes.
This command is provided for the eventual operator run; the recorded October
2026 failure should not be replaced with a successful-looking example.

With the assigned tenant, hosted context and token environment variables set,
the small actual experiment is:

```bash
python probe.py measure --output ../../rerun/toolbox-experiment
```

The sequence is explicit:

1. Fetch and compare the hosted context, then check only the six proposed
   UUID-scoped identifiers for collisions.
2. Create three synthetic `DataQualityAssessment` entities and three linked
   `AirQualityObserved` entities using `application/ld+json` and the complete
   inline context. A confirmed HTTP 201 establishes each ownership receipt.
3. Query all three observations and query the exact same identifiers with
   `NO2.qualityScore>=0.98;NO2.qualityLevel=="valid"`. The expected result is one
   eligible observation; a low-score case and a high-score/failed-gate case
   must be excluded. An unsupported nested query is recorded as failure; the
   harness does not silently replace it with client-side filtering.
4. Record seven baseline and seven quality-query HTTP samples after one warmup
   of each, alternating order and pausing between requests. The repetition
   limit is 30, and no concurrent load is generated.
5. Retrieve the linked evidence with the consumer credential, check its run
   and target links, compare the exact fixture-input hash, and evaluate the
   declared score and hardware gate. The measurement and unit must agree with
   the hashed fixture inputs. Expected decisions are one accept and two
   quarantines. These are synthetic decisions, not sensor error-rate estimates.
6. Fetch each entity whose POST returned 201, check its UUID run marker and
   synthetic marker, delete that exact entity, and verify it is absent.

The direct gateway route is deliberate. The [pinned Python backend client](https://code.europa.eu/ldt-toolbox/eu_ldt_data_platform/-/blob/efc368c81a4e78d61615ba32b17c1c8dac35a174/backend-py/src/services/context_brokering_clients/scorpio_broker_client.py)
removes the inline `@context` in its `create_entity` method before submitting
`application/json` to Scorpio. The harness therefore exercises the direct
NGSI-LD route so that custom vocabulary terms have their supplied meaning.
It does not assume the UI wrapper and direct API have identical behavior.

## Output and interpretation

`requests.jsonl` captures the method, operation, relative path, status,
client-observed elapsed time, request/response body sizes and response digest
for every request, including failures. Tokens, response bodies, claims and
internal authentication headers are not recorded. `run_result.json` preserves
the complete status, per-entity ownership receipts, consumer decisions,
raw request records and descriptive query timing summaries. The original
synthetic request payloads and exact hash inputs are saved separately.

The baseline returns three observations and the quality query returns one.
Their timings therefore measure different response sizes as well as different
query predicates. They cannot isolate the cost of quality reasoning or support
a throughput, scalability or end-to-end sensor-latency claim. Samples include
TLS/HTTP, gateway, broker and response reading. A fresh urllib request is used
for each sample. Token acquisition, context preflight, creation, evidence fetch
and cleanup are excluded from the query summaries. These scope details must
accompany any future reported numbers.

The harness uses one API endpoint and one client process, with an optional
second credential for reads. It does not test a second broker, a data-space
connector, contract/policy negotiation, subscription delivery or independent
organizational trust. Its fixture scores and hardware flags are predeclared
inputs; it does not recalculate laboratory uncertainty or authenticate original
reports. The hash verifies consistency with synthetic fixture bytes only.

Cleanup never enumerates or deletes a tenant, data source, subscription or
foreign identifier. An HTTP 409 is not an ownership receipt. A timeout or 5xx
after POST may leave an indeterminate entity; its exact identifier is recorded
for operator review and is not deleted automatically. If an ownership marker
changes, deletion is skipped. Deletion confirms absence from the entity API;
it does not promise removal of retained audit logs or temporal/database
history. `cleanup_complete` must be checked even when fixture checks passed.

## Relationship to the earlier supplement

The existing Orion-LD two-broker Compose recipe remains an **alternative,
unexecuted recipe**. It is not the actual Toolbox deployment. This directory
is the proposed primary Toolbox-specific integration path. Existing local
benchmark values, `source-unverified` states, and the captured flags for
unexecuted broker/connector/municipal experiments remain unchanged until
actual successful evidence is captured and reviewed.
