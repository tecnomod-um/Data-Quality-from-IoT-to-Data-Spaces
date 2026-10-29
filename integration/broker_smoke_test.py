#!/usr/bin/env python3
"""OPTIONAL AND UNEXECUTED: check a proposed two-broker exchange recipe.

This script is supplied for the authors to execute on an actual broker testbed.
It has not been executed in the manuscript revision environment. A successful
run would still not demonstrate a data-space connector, authorization, mutual
organizational trust, or city-scale interoperability.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from run_validation import CONTEXT, canonical_bytes, fixture_key, observation, prop, rel, runtime_assessment

CONTEXT_URL = "http://contexts:8080/data-quality-context.jsonld"

def http(base, method, path, body=None):
    headers = {"Accept": "application/ld+json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/ld+json"
        data = json.dumps(body).encode()
    else:
        headers["Link"] = '<' + CONTEXT_URL + '>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'
    req = Request(base.rstrip("/") + path, data=data, headers=headers, method=method)
    with urlopen(req, timeout=30) as response:
        raw = response.read()
        return response.status, json.loads(raw) if raw else None

def create(base, entity):
    status, _ = http(base, "POST", "/ngsi-ld/v1/entities", entity)
    assert status == 201, status

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--producer", default="http://127.0.0.1:1026")
    parser.add_argument("--consumer", default="http://127.0.0.1:1027")
    parser.add_argument("--output", type=Path, default=Path("broker_results_after_author_run.json"))
    args = parser.parse_args()
    # Unique run namespace avoids deleting any pre-existing test data.
    run = str(time.time_ns())
    assessment_id = "urn:ngsi-ld:DataQualityAssessment:integration:" + run
    baseline_fixture = observation(0)
    baseline_digest = hashlib.sha256(canonical_bytes(baseline_fixture)).hexdigest()
    assessment = runtime_assessment(0, 1, baseline_digest)
    assessment.update(id=assessment_id, **{"@context": CONTEXT})
    # The digest covers an explicit synthetic baseline fixture, not a report.
    assessment["evidenceIntegrityStatus"] = prop("synthetic-fixture")
    assessment["evidenceHashScope"] = prop("canonical_bytes(observation(0)) synthetic baseline fixture")
    entities = []
    for suffix, score, level in [("accepted", 59/60, "valid"), ("low-score", 0.7, "quarantine"),
                                 ("failed-gate", 59/60, "quarantine")]:
        entity = observation(0)
        entity["id"] = "urn:ngsi-ld:AirQualityObserved:integration:" + run + ":" + suffix
        entity["@context"] = CONTEXT
        entity["NO2"].update(qualityScore=prop(score), qualityLevel=prop(level),
                              hasQualityAssessment=rel(assessment_id))
        entities.append(entity)
    create(args.producer, assessment)
    for entity in entities:
        create(args.producer, entity)
    query = urlencode({"type": "AirQualityObserved",
                       "id": ",".join(e["id"] for e in entities),
                       "q": 'NO2.qualityScore>=0.98;NO2.qualityLevel=="valid"'})
    # If nested attribute querying is unsupported, preserve the error and do
    # not count that run as successful interoperability.
    start = time.perf_counter_ns()
    status, selected = http(args.producer, "GET", "/ngsi-ld/v1/entities?" + query)
    query_ms = (time.perf_counter_ns() - start) / 1e6
    assert status == 200 and len(selected) == 1, selected
    assert selected[0]["id"] == entities[0]["id"]
    # Exact-byte signed envelope between producer and consumer client roles.
    _, retrieved_assessment = http(args.producer, "GET", "/ngsi-ld/v1/entities/" + quote(assessment_id, safe=""))
    envelope = canonical_bytes({"observation": selected[0], "assessment": retrieved_assessment, "synthetic": True})
    key = fixture_key(); signature = key.sign(envelope)
    key.public_key().verify(signature, envelope)
    received = json.loads(envelope)
    create(args.consumer, received["assessment"])
    create(args.consumer, received["observation"])
    status, fetched = http(args.consumer, "GET", "/ngsi-ld/v1/entities/" + quote(entities[0]["id"], safe=""))
    assert status == 200 and fetched["id"] == entities[0]["id"]
    args.output.write_text(json.dumps({"executed_by_author": True, "query_matches": 1,
                                       "single_query_elapsed_ms": query_ms,
                                       "two_broker_roundtrip": True, "signature_test_key_only": True,
                                       "connector_tested": False,
                                       "warning": "One smoke test is not an overhead benchmark."}, indent=2) + "\n")
    print(args.output)

if __name__ == "__main__":
    main()
