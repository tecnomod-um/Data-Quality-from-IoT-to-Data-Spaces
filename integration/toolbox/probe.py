#!/usr/bin/env python3
"""Bounded EU LDT Toolbox NGSI-LD replication harness; default mode is offline.

This is a proposed integration artifact. Its offline tests are not broker results.
Credentials come only from environment variables and are never written to output.
The direct /cb route preserves the inline custom context supplied on entity POSTs.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import statistics
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener
import uuid


NAMESPACE = "https://example.org/dq-profile#"
MAX_RESPONSE_BYTES = 1024 * 1024
TOKEN_ENV = "LDT_ACCESS_TOKEN"
CONSUMER_TOKEN_ENV = "LDT_CONSUMER_ACCESS_TOKEN"


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    """Exact implementation byte contract; not general JSON/RDF canonicalization."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


class CheckFailure(Exception):
    """Contains only a fixed, non-secret diagnostic label."""


class NoRedirect(HTTPRedirectHandler):
    """Never forward a bearer token through a redirect, including same-origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class Reply:
    status: int
    body: bytes
    content_type: str = "application/json"


class HTTPTransport:
    kind = "https_network"

    def __init__(self, timeout, ca_bundle=None):
        context = ssl.create_default_context(cafile=ca_bundle)
        self.opener = build_opener(NoRedirect(), HTTPSHandler(context=context))
        self.timeout = timeout

    def __call__(self, method, url, headers, body):
        request = Request(url, data=body, headers=headers, method=method)
        try:
            response = self.opener.open(request, timeout=self.timeout)
        except HTTPError as error:
            response = error
        with response:
            content = response.read(MAX_RESPONSE_BYTES + 1)
            if len(content) > MAX_RESPONSE_BYTES:
                raise CheckFailure("response_exceeds_one_megabyte_limit")
            return Reply(response.status, content,
                         response.headers.get("Content-Type", "").split(";")[0])


def valid_https(value):
    if not isinstance(value, str) or any(character.isspace() or character in '<>"'
                                         for character in value):
        raise CheckFailure("url_contains_invalid_header_characters")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise CheckFailure("https_url_without_credentials_query_or_fragment_required")
    return value.rstrip("/")


def load_config(path):
    config = json.loads(path.read_text())
    overrides = {
        "api_base_url": "LDT_API_BASE_URL", "tenant": "LDT_NGSILD_TENANT",
        "context_url": "LDT_CONTEXT_URL", "ca_bundle": "LDT_CA_BUNDLE",
    }
    for key, env in overrides.items():
        if os.environ.get(env):
            config[key] = os.environ[env]
    config["api_base_url"] = valid_https(config["api_base_url"])
    if not urlsplit(config["api_base_url"]).path.endswith("/ngsi-ld/v1"):
        raise CheckFailure("api_base_must_end_in_ngsi_ld_v1")
    if config.get("context_url"):
        config["context_url"] = valid_https(config["context_url"])
    if config.get("tenant") and not re.fullmatch(r"[a-z0-9_]+", config["tenant"]):
        raise CheckFailure("tenant_must_match_pinned_opa_scope_pattern")
    for key, lower, upper in [("timeout_seconds", 1, 60), ("repetitions", 1, 30),
                              ("pause_seconds", 0.1, 5)]:
        value = config[key]
        if isinstance(value, bool) or not lower <= value <= upper:
            raise CheckFailure("configuration_outside_bounded_limits")
    if not isinstance(config["repetitions"], int):
        raise CheckFailure("integer_repetition_count_required")
    config["context_file"] = str((path.parent / config["context_file"]).resolve())
    return config


def prop(value):
    return {"type": "Property", "value": value}


def rel(value):
    return {"type": "Relationship", "object": value}


def fixtures(run_id, context):
    """Three declared synthetic decisions; one separate assessment per observation."""
    cases = [("eligible", 59 / 60, True, "valid"),
             ("low_score", 0.7, True, "quarantine"),
             ("failed_gate", 59 / 60, False, "quarantine")]
    observations, assessments, inputs = [], [], {}
    for name, score, hardware, level in cases:
        oid = f"urn:ngsi-ld:AirQualityObserved:dq-replication:{run_id}:{name}"
        aid = f"urn:ngsi-ld:DataQualityAssessment:dq-replication:{run_id}:{name}"
        evidence = {"testRun": run_id, "testCase": name, "NO2": 42.1,
                    "unitCode": "GQ", "qualityScore": score,
                    "hardwareHealthy": hardware, "synthetic": True}
        inputs[aid] = evidence
        common = {"@context": context, "testRun": prop(run_id),
                  "testCase": prop(name), "synthetic": prop(True)}
        assessments.append({
            **common, "id": aid, "type": "DataQualityAssessment",
            "refEntity": rel(oid), "refProperty": prop("NO2"),
            "metricCode": prop("synthetic_precomputed_query_fixture"),
            "metricValue": prop(score), "thresholdMin": prop(0.98),
            "hardwareHealthy": prop(hardware),
            "decision": prop("accept" if name == "eligible" else "quarantine"),
            "evidenceHash": prop("sha256:" + hashlib.sha256(encode(evidence)).hexdigest()),
            "evidenceHashScope": prop("encode of this assessment's entry in fixture_inputs.json"),
            "evidenceIntegrityStatus": prop("synthetic-fixture-only"),
        })
        observations.append({
            **common, "id": oid, "type": "AirQualityObserved",
            "NO2": {**prop(42.1), "unitCode": "GQ",
                    "qualityScore": prop(score), "qualityLevel": prop(level),
                    "hasQualityAssessment": rel(aid)},
        })
    return observations, assessments, inputs


def one_attribute(entity, key):
    if not isinstance(entity, dict):
        raise CheckFailure("entity_or_attribute_is_not_an_object")
    value = entity.get(key, entity.get(NAMESPACE + key))
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if not isinstance(value, dict):
        raise CheckFailure("missing_or_ambiguous_fixture_attribute")
    return value


def scalar(entity, key, relationship=False):
    attr = one_attribute(entity, key)
    field = "object" if relationship else "value"
    if field not in attr:
        raise CheckFailure("missing_normalized_attribute_value")
    return attr[field]


class Harness:
    def __init__(self, config, output, producer_token=None, consumer_token=None,
                 transport=None):
        self.config, self.output = config, output
        self.producer_token = producer_token
        self.consumer_token = consumer_token or producer_token
        self.transport = transport
        self.run_id = uuid.uuid4().hex
        self.receipts, self.unknown_creates, self.requests = [], [], []
        self.context = json.loads(Path(config["context_file"]).read_text())["@context"]
        self.observations, self.assessments, self.inputs = fixtures(self.run_id, self.context)
        self.all_entities = self.assessments + self.observations
        self.result = {
            "artifact_kind": "proposed_integration_harness_run",
            "run_id": self.run_id, "started_at_utc": now(),
            "source_reference": {"tag": config["source_tag"],
                                 "commit": config["source_commit"]},
            "api_base_url": config["api_base_url"], "tenant": config.get("tenant"),
            "runtime_broker_version_verified": False,
            "separate_token_values_supplied": bool(consumer_token and producer_token
                                                    and consumer_token != producer_token),
            "independent_organizations_verified": False,
            "data_space_connector_executed": False,
            "subscription_delivery_tested": False,
            "municipal_deployment_evaluated": False,
            "successful_ngsi_ld_fixture_roundtrip": False,
            "successful_network_fixture_roundtrip": False,
            "quality_query_verified": False,
            "cleanup_complete": None,
        }

    def save(self):
        self.result["ownership_receipts"] = self.receipts
        self.result["indeterminate_create_ids"] = self.unknown_creates
        self.result["requests"] = self.requests
        write_json(self.output / "run_result.json", self.result)

    def call(self, method, path, operation, body=None, consumer=False,
             context_request=False, resource_id=None):
        if self.transport is None:
            self.transport = HTTPTransport(self.config["timeout_seconds"],
                                           self.config.get("ca_bundle"))
        headers = {"Accept": "application/ld+json"}
        token = self.consumer_token if consumer else self.producer_token
        if not context_request:
            if token:
                headers["Authorization"] = "Bearer " + token
            if self.config.get("tenant"):
                headers["NGSILD-Tenant"] = self.config["tenant"]
            if self.config.get("context_url"):
                headers["Link"] = (
                    f'<{self.config["context_url"]}>; '
                    'rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'
                )
        payload = encode(body) if body is not None else None
        if payload is not None:
            headers["Content-Type"] = "application/ld+json"
            # Inline context is authoritative for entity creation.
            headers.pop("Link", None)
        url = path if context_request else self.config["api_base_url"] + path
        record = {"at_utc": now(), "operation": operation, "method": method,
                  "path": path, "resource_id": resource_id,
                  "request_body_bytes": len(payload or b""),
                  "authentication_attached": bool(token and not context_request),
                  "credential_role": "consumer" if consumer else "producer"}
        start = time.perf_counter_ns()
        try:
            reply = self.transport(method, url, headers, payload)
            record.update(status=reply.status, response_body_bytes=len(reply.body),
                          response_sha256=hashlib.sha256(reply.body).hexdigest(),
                          response_content_type=reply.content_type)
            return reply
        except (OSError, URLError, CheckFailure) as error:
            record.update(status=None, error_type=type(error).__name__)
            # Do not serialize exception text, headers, URLs with credentials or tokens.
            raise CheckFailure("transport_failed_no_retry") from None
        finally:
            record["elapsed_ms"] = (time.perf_counter_ns() - start) / 1e6
            self.requests.append(record)
            with (self.output / "requests.jsonl").open("a") as ledger:
                ledger.write(json.dumps(record) + "\n")
            self.save()

    @staticmethod
    def json_reply(reply, expected_status=200):
        if reply.status != expected_status:
            raise CheckFailure(f"unexpected_http_status_{reply.status}")
        try:
            return json.loads(reply.body)
        except (ValueError, UnicodeError):
            raise CheckFailure("response_is_not_json") from None

    def list_query(self, quality=False, label="query"):
        params = {"type": "AirQualityObserved",
                  "id": ",".join(item["id"] for item in self.observations),
                  "limit": len(self.observations)}
        if quality:
            params["q"] = 'NO2.qualityScore>=0.98;NO2.qualityLevel=="valid"'
        reply = self.call("GET", "/entities?" + urlencode(params), label, consumer=True)
        entities = self.json_reply(reply)
        if not isinstance(entities, list):
            raise CheckFailure("query_response_is_not_a_list")
        expected = {self.observations[0]["id"]} if quality else {
            item["id"] for item in self.observations}
        actual = [item.get("id") for item in entities if isinstance(item, dict)]
        if (set(actual) != expected or len(actual) != len(expected)
                or len(entities) != len(expected)):
            raise CheckFailure("query_did_not_return_exact_expected_owned_ids")
        return entities

    def consume(self, observations):
        decisions = []
        by_id = {item["id"]: item for item in self.assessments}
        for observation in observations:
            no2 = one_attribute(observation, "NO2")
            aid = scalar(no2, "hasQualityAssessment", relationship=True)
            if aid not in by_id:
                raise CheckFailure("assessment_link_leaves_run_namespace")
            reply = self.call("GET", "/entities/" + quote(aid, safe=""),
                              "consumer_fetch_evidence", consumer=True, resource_id=aid)
            assessment = self.json_reply(reply)
            if (not isinstance(assessment, dict) or assessment.get("id") != aid
                    or scalar(assessment, "testRun") != self.run_id
                    or scalar(observation, "testRun") != self.run_id
                    or scalar(assessment, "refEntity", True) != observation["id"]):
                raise CheckFailure("evidence_target_or_run_mismatch")
            score = scalar(no2, "qualityScore")
            expected_hash = "sha256:" + hashlib.sha256(encode(self.inputs[aid])).hexdigest()
            gates = {
                "score": isinstance(score, (int, float)) and not isinstance(score, bool)
                         and score >= 0.98,
                "cached_quality_level": scalar(no2, "qualityLevel") == "valid",
                "assessment_score_agrees": scalar(assessment, "metricValue") == score
                                           and score == self.inputs[aid]["qualityScore"],
                "measurement_value_agrees": scalar(observation, "NO2") == self.inputs[aid]["NO2"]
                                            and no2.get("unitCode") == self.inputs[aid]["unitCode"],
                "hardware_fixture": scalar(assessment, "hardwareHealthy") is True,
                "fixture_hash_matches": scalar(assessment, "evidenceHash") == expected_hash,
                "synthetic_marker": scalar(assessment, "synthetic") is True
                                    and scalar(observation, "synthetic") is True,
            }
            decisions.append({"entity_id": observation["id"], "assessment_id": aid,
                              "decision": "accept" if all(gates.values()) else "quarantine",
                              "failed_gates": [name for name, passed in gates.items() if not passed]})
        accepted = {item["entity_id"] for item in decisions if item["decision"] == "accept"}
        if accepted != {self.observations[0]["id"]} or len(decisions) != 3:
            raise CheckFailure("consumer_decisions_differ_from_declared_fixture")
        self.result["consumer_decisions"] = decisions

    def cleanup(self):
        for receipt in reversed(self.receipts):
            eid = receipt["id"]
            try:
                reply = self.call("GET", "/entities/" + quote(eid, safe=""),
                                  "cleanup_verify_ownership", resource_id=eid)
                if reply.status == 404:
                    receipt["cleanup"] = "already_absent"
                    continue
                entity = self.json_reply(reply)
                if (not isinstance(entity, dict) or entity.get("id") != eid
                        or scalar(entity, "testRun") != self.run_id
                        or scalar(entity, "synthetic") is not True):
                    receipt["cleanup"] = "skipped_ownership_mismatch"
                    continue
                reply = self.call("DELETE", "/entities/" + quote(eid, safe=""),
                                  "delete_owned_fixture", resource_id=eid)
                if reply.status != 204:
                    raise CheckFailure("cleanup_delete_not_confirmed")
                reply = self.call("GET", "/entities/" + quote(eid, safe=""),
                                  "cleanup_verify_absent", resource_id=eid)
                receipt["cleanup"] = "confirmed_absent" if reply.status == 404 else "absence_unconfirmed"
            except CheckFailure as error:
                receipt["cleanup"] = str(error)
            finally:
                self.save()
        self.result["cleanup_complete"] = (
            not self.unknown_creates and all(item.get("cleanup") in
                {"confirmed_absent", "already_absent"} for item in self.receipts)
        )

    def measure(self):
        if not self.producer_token or not self.config.get("tenant") or not self.config.get("context_url"):
            raise CheckFailure("measure_requires_token_assigned_tenant_and_hosted_context")
        reply = self.call("GET", self.config["context_url"], "verify_hosted_context", context_request=True)
        hosted = self.json_reply(reply)
        if hosted != {"@context": self.context}:
            raise CheckFailure("hosted_context_differs_from_bundled_context")
        # Preflight only the six exact IDs; never enumerate all tenant data.
        params = {"id": ",".join(item["id"] for item in self.all_entities), "limit": 6}
        reply = self.call("GET", "/entities?" + urlencode(params), "check_ids_absent")
        if self.json_reply(reply) != []:
            raise CheckFailure("run_namespace_collision_no_mutation_performed")
        for entity in self.all_entities:
            try:
                reply = self.call("POST", "/entities", "create_synthetic_fixture",
                                  entity, resource_id=entity["id"])
            except CheckFailure:
                self.unknown_creates.append(entity["id"])
                raise
            if reply.status != 201:
                if reply.status >= 500:
                    self.unknown_creates.append(entity["id"])
                raise CheckFailure(f"create_not_confirmed_http_{reply.status}")
            self.receipts.append({"id": entity["id"], "creation_status": 201,
                                  "testRun": self.run_id, "cleanup": "pending"})
            self.save()
        self.list_query(label="warmup_baseline_query")
        self.list_query(quality=True, label="warmup_quality_query")
        for repeat in range(self.config["repetitions"]):
            for quality in ([False, True] if repeat % 2 == 0 else [True, False]):
                self.list_query(quality, "quality_query" if quality else "baseline_query")
                time.sleep(self.config["pause_seconds"])
        baseline = self.list_query(label="consumer_retrieve_all_cases")
        self.consume(baseline)
        self.result["successful_ngsi_ld_fixture_roundtrip"] = True
        self.result["successful_network_fixture_roundtrip"] = self.transport.kind == "https_network"
        self.result["quality_query_verified"] = True
        self.result["timing_scope"] = (
            "Client-observed sequential HTTP request wall time including TLS/HTTP, gateway, "
            "broker and response read; no sensor latency, server-only time, throughput or load claim. "
            "A fresh urllib request is used per sample; token acquisition, context preflight, "
            "fixture creation, evidence fetch and cleanup are excluded from query summaries."
        )
        self.result["query_timings"] = {}
        for name in ("baseline_query", "quality_query"):
            rows = [item for item in self.requests if item["operation"] == name]
            values = [item["elapsed_ms"] for item in rows]
            self.result["query_timings"][name] = {
                "samples": len(values), "median_ms": statistics.median(values),
                "min_ms": min(values), "max_ms": max(values),
                "response_body_bytes": [item["response_body_bytes"] for item in rows],
            }

    def run(self, mode):
        self.output.mkdir(parents=True, exist_ok=False)
        write_json(self.output / "fixtures.jsonld", self.all_entities)
        write_json(self.output / "fixture_inputs.json", self.inputs)
        self.result["mode"] = mode
        self.result["status"] = "started"
        self.result["planned_fixture_entities"] = 6
        self.result["planned_quality_query"] = 'NO2.qualityScore>=0.98;NO2.qualityLevel=="valid"'
        try:
            if mode == "plan":
                self.result["status"] = "planned_no_network_requests"
            elif mode == "probe":
                eid = "urn:ngsi-ld:DataQualityProbe:nonexistent:" + self.run_id
                reply = self.call("GET", "/entities?" + urlencode({"id": eid, "limit": 1}),
                                  "read_only_reachability_probe", resource_id=eid)
                self.result["probe_http_status"] = reply.status
                self.result["status"] = "http_response_observed_no_mutations"
                self.result["probe_interpretation"] = {
                    200: "API responded; no deployment, write permission or quality result established.",
                    401: "Authentication required; no access established.",
                    403: "Request forbidden; no permission or deployment result established.",
                    503: "Service unavailable; no application experiment executed.",
                }.get(reply.status, "HTTP response only; investigate without changing routes or privileges.")
            elif mode == "measure":
                self.measure()
                self.result["status"] = "fixture_checks_passed"
            else:
                raise CheckFailure("unknown_mode")
        except CheckFailure as error:
            self.result["status"] = "failed"
            self.result["failure"] = str(error)
        except KeyboardInterrupt:
            self.result["status"] = "interrupted"
        finally:
            if mode == "measure":
                self.cleanup()
                if self.result["status"] == "fixture_checks_passed" and not self.result["cleanup_complete"]:
                    self.result["status"] = "fixture_checks_passed_cleanup_incomplete"
            self.result["transport_kind"] = self.transport.kind if self.transport else "none"
            self.result["finished_at_utc"] = now()
            self.save()
        return self.result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["plan", "probe", "measure"], nargs="?", default="plan")
    parser.add_argument("--config", type=Path,
                        default=Path(__file__).with_name("config.example.json"))
    parser.add_argument("--output", type=Path, required=True,
                        help="New directory; existing outputs are never overwritten.")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        harness = Harness(config, args.output, os.environ.get(TOKEN_ENV),
                          os.environ.get(CONSUMER_TOKEN_ENV))
        result = harness.run(args.mode)
    except (CheckFailure, ValueError, OSError) as error:
        # Input/config errors may contain paths but should never expose credentials.
        print("Input/output failure:", type(error).__name__)
        return 2
    print(json.dumps({"status": result["status"], "output": str(args.output)}))
    return 0 if result["status"] in {"planned_no_network_requests", "fixture_checks_passed",
                                      "http_response_observed_no_mutations"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
