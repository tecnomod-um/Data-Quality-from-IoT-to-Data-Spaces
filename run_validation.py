#!/usr/bin/env python3
"""Reproduce the manuscript revision's local evidence checks and synthetic tests.

This is NOT an NGSI-LD context broker, a deployed data space, or a field trial.
All timings measure a local serialization/hash/signing path, without networking,
database writes, indexing, subscriptions, or identity infrastructure.
"""
from __future__ import annotations

import argparse
import copy
from collections import Counter
import csv
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
import time

HERE = Path(__file__).resolve().parent
if (HERE / "vendor").exists():
    sys.path.insert(0, str(HERE / "vendor"))

import jsonschema
import rdflib
from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD
from rdflib.compare import isomorphic
from pyshacl import validate as shacl_validate
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.exceptions import InvalidSignature

DQ = Namespace("https://example.org/dq-profile#")
NGSI = Namespace("https://uri.etsi.org/ngsi-ld/")
DQV = Namespace("http://www.w3.org/ns/dqv#")
PROV = Namespace("http://www.w3.org/ns/prov#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DCT = Namespace("http://purl.org/dc/terms/")
SCHEMA_URI = "urn:revision:schemas:DataQualityAssessment:1"

CONTEXT = {
    "id": "@id", "type": "@type",
    "Property": str(NGSI.Property), "Relationship": str(NGSI.Relationship),
    "value": str(NGSI.hasValue),
    "object": {"@id": str(NGSI.hasObject), "@type": "@id"},
    "observedAt": {"@id": str(NGSI.observedAt), "@type": str(XSD.dateTime)},
    "unitCode": str(NGSI.unitCode),
    "AirQualityObserved": "https://smartdatamodels.org/dataModel.Environment/AirQualityObserved",
}
for term in ("DataQualityAssessment", "SensorQualityProfile", "NO2", "refEntity", "refProperty",
             "phase", "standard", "pollutant", "device", "dimension", "metricCode", "metricValue",
             "unit", "thresholdMin", "thresholdMax", "result", "contextWindow", "evaluator",
             "evidenceSource", "qualityClass", "evidenceHash", "evidenceHashScope",
             "evidenceIntegrityStatus", "sourceRecord", "qualityScore", "qualityLevel",
             "hasQualityAssessment", "completeness", "freshness", "schemaScore", "sampleCount",
             "expectedCount", "policyVersion", "synthetic", "windowStart", "windowEnd",
             "refDevice", "sourceApplicability", "decision", "reason", "sequence"):
    CONTEXT[term] = str(DQ[term])

POLICY = {
    "id": "urn:revision:policy:synthetic-runtime:1",
    "synthetic": True,
    "expected_samples": 60,
    "window_seconds": 60,
    "weights": {"completeness": 0.5, "freshness": 0.3, "schema": 0.2},
    "freshness_grace_seconds": 60,
    "freshness_decay_seconds": 60,
    "gate_min_completeness": 0.9,
    "gate_max_age_seconds": 120,
    "gate_schema_score": 1.0,
    "minimum_aggregate": 0.9,
    "unit": "synthetic-S01", "firmware": "v1", "scope": "site-A",
    "note": "Illustrative policy, not calibrated from the CEN certificates or a municipal service.",
}

def canonical_bytes(value):
    """Profile-specific JSON byte contract, NOT general RFC 8785/RDF canonicalization."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")

def sha(value):
    return hashlib.sha256(value).hexdigest()

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n")

def prop(value):
    return {"type": "Property", "value": value}

def rel(value):
    return {"type": "Relationship", "object": value}

def assertion_schema():
    text = {"type": "object", "required": ["type", "value"], "additionalProperties": False,
            "properties": {"type": {"const": "Property"}, "value": {"type": "string", "minLength": 1}}}
    number = copy.deepcopy(text)
    number["properties"]["value"] = {"type": "number"}
    relationship = {"type": "object", "required": ["type", "object"], "additionalProperties": False,
                    "properties": {"type": {"const": "Relationship"},
                                   "object": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9+.-]*:"}}}
    fields = ["refEntity", "refProperty", "phase", "standard", "dimension", "metricCode", "metricValue",
              "unit", "result", "contextWindow", "evaluator", "evidenceSource", "evidenceHash",
              "evidenceHashScope", "evidenceIntegrityStatus", "sourceRecord"]
    properties = {"id": {"type": "string", "pattern": "^urn:ngsi-ld:DataQualityAssessment:"},
                  "type": {"const": "DataQualityAssessment"}, "@context": {"type": "object"}}
    for field in fields + ["thresholdMin", "thresholdMax", "qualityClass", "pollutant", "device"]:
        properties[field] = copy.deepcopy(relationship if field in ["refEntity", "sourceRecord"] else
                                          number if field in ["metricValue", "thresholdMin", "thresholdMax"] else text)
    properties["evidenceHash"]["properties"]["value"] = {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}
    properties["evidenceIntegrityStatus"]["properties"]["value"] = {"const": "source-unverified"}
    properties["result"]["properties"]["value"] = {"enum": ["pass", "fail", "unknown"]}
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA_URI,
            "title": "Revision certificate-derived NGSI-LD assessment application profile",
            "description": "Structural application profile; not ETSI conformance or report authentication.",
            "type": "object", "required": ["id", "type", "@context"] + fields,
            "properties": properties, "additionalProperties": False,
            "anyOf": [{"required": ["thresholdMin"]}, {"required": ["thresholdMax"]}]}

def normalize_record(record, disambiguate=False):
    r = copy.deepcopy(record)
    r["evaluator"] = "Laboratory L1 (reported evaluator; identity withheld)"
    r["evidenceSource"] = "Author-supplied transcription of laboratory/field report; original report unavailable in this package"
    raw_hash = sha(canonical_bytes(r))
    entity_id = r["id"]
    if disambiguate:
        entity_id += ":context-" + sha(r["contextWindow"].encode("utf-8"))[:12]
    target = "urn:ngsi-ld:SensorGroup:D1-D3" if r["metricCode"] == "u_between_sensors" else "urn:ngsi-ld:Device:" + r["device"]
    entity = {"id": entity_id, "type": "DataQualityAssessment", "@context": CONTEXT,
              "refEntity": rel(target),
              "refProperty": prop(r["pollutant"]),
              "evidenceHash": prop("sha256:" + raw_hash),
              "evidenceHashScope": prop("anonymized supplied record serialized by canonical_bytes in run_validation.py"),
              "evidenceIntegrityStatus": prop("source-unverified"),
              "sourceRecord": rel("urn:sha256:" + raw_hash)}
    for k, v in r.items():
        if k not in ["id", "type"] and v is not None:
            entity[k] = prop(v)
    return r, entity

SHAPES = """@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix dqv: <http://www.w3.org/ns/dqv#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix ex: <https://example.org/dq-profile#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:QualityMeasurementShape a sh:NodeShape ; sh:targetClass dqv:QualityMeasurement ;
 sh:property [ sh:path dqv:computedOn ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:IRI ] ;
 sh:property [ sh:path dqv:isMeasurementOf ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:IRI ] ;
 sh:property [ sh:path dqv:value ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:double ] ;
 sh:property [ sh:path prov:wasDerivedFrom ; sh:minCount 1 ; sh:nodeKind sh:IRI ] ;
 sh:property [ sh:path prov:wasGeneratedBy ; sh:minCount 1 ; sh:nodeKind sh:IRI ] ;
 sh:property [ sh:path ex:unit ; sh:minCount 1 ; sh:datatype xsd:string ] ;
 sh:property [ sh:path ex:evidenceIntegrityStatus ; sh:hasValue "source-unverified" ; sh:maxCount 1 ] .
ex:DatasetShape a sh:NodeShape ; sh:targetClass dcat:Dataset ;
 sh:property [ sh:path dct:title ; sh:minCount 1 ] ;
 sh:property [ sh:path dcat:distribution ; sh:minCount 1 ; sh:class dcat:Distribution ] .
ex:DistributionShape a sh:NodeShape ; sh:targetClass dcat:Distribution ;
 sh:property [ sh:path dcat:mediaType ; sh:minCount 1 ] .
"""

QUERY = """PREFIX dqv: <http://www.w3.org/ns/dqv#>
PREFIX ex: <https://example.org/dq-profile#>
SELECT ?measurement ?value ?limit WHERE {
 ?measurement a dqv:QualityMeasurement ; dqv:isMeasurementOf ex:expanded_uncertainty_at_limit ;
 dqv:value ?value ; ex:thresholdMax ?limit .
 FILTER (?value / ?limit > 0.90)
} ORDER BY ?measurement
"""

def rdf_export(records, entities):
    graph = Graph()
    for prefix, ns in [("ex", DQ), ("dqv", DQV), ("prov", PROV), ("dcat", DCAT), ("dct", DCT)]:
        graph.bind(prefix, ns)
    dataset = URIRef("urn:revision:dataset:certificate-transcriptions")
    distribution = URIRef("urn:revision:distribution:normalized-jsonld")
    activity = URIRef("urn:revision:activity:transcription-mapping")
    agent = URIRef("urn:revision:agent:mapping-script")
    graph.add((dataset, RDF.type, DCAT.Dataset))
    graph.add((dataset, DCT.title, Literal("Anonymized certificate-derived assertions; original reports unverified")))
    graph.add((dataset, DCAT.distribution, distribution))
    graph.add((distribution, RDF.type, DCAT.Distribution))
    graph.add((distribution, DCAT.mediaType, Literal("application/ld+json")))
    graph.add((activity, RDF.type, PROV.Activity))
    graph.add((activity, PROV.wasAssociatedWith, agent))
    graph.add((agent, RDF.type, PROV.SoftwareAgent))
    for r, entity in zip(records, entities):
        node = URIRef(entity["id"])
        source = URIRef("urn:sha256:" + sha(canonical_bytes(r)))
        target = URIRef(entity["refEntity"]["object"])
        graph.add((dataset, DQV.hasQualityMeasurement, node))
        graph.add((node, RDF.type, DQV.QualityMeasurement))
        graph.add((node, DQV.computedOn, target))
        graph.add((node, DQV.isMeasurementOf, DQ[r["metricCode"]]))
        graph.add((node, DQV.value, Literal(float(r["metricValue"]), datatype=XSD.double)))
        graph.add((node, PROV.wasDerivedFrom, source))
        graph.add((node, PROV.wasGeneratedBy, activity))
        graph.add((source, RDF.type, PROV.Entity))
        graph.add((node, DQ.unit, Literal(r["unit"], datatype=XSD.string)))
        graph.add((node, DQ.evidenceIntegrityStatus, Literal("source-unverified")))
        graph.add((node, DQ.contextWindow, Literal(r["contextWindow"])))
        graph.add((node, DQ.refProperty, Literal(r["pollutant"])))
        for key in ["thresholdMin", "thresholdMax"]:
            if r[key] is not None:
                graph.add((node, DQ[key], Literal(float(r[key]), datatype=XSD.double)))
    return graph

def check_sources(input_path, output):
    original = json.loads(input_path.read_text())["@graph"]
    id_counts = Counter(r["id"] for r in original)
    normalized_pairs = [normalize_record(r, id_counts[r["id"]] > 1) for r in original]
    records, entities = zip(*normalized_pairs)
    schema = assertion_schema()
    validator = jsonschema.Draft202012Validator(schema)
    jsonschema.Draft202012Validator.check_schema(schema)
    errors = [dict(id=e["id"], errors=[v.message for v in validator.iter_errors(e)]) for e in entities]
    assert not any(x["errors"] for x in errors), errors
    assert len(set(x["id"] for x in entities)) == len(entities)
    recomputed = []
    for r in records:
        good = ((r["thresholdMin"] is None or r["metricValue"] >= r["thresholdMin"]) and
                (r["thresholdMax"] is None or r["metricValue"] <= r["thresholdMax"]))
        recomputed.append(good)
        assert (r["result"] == "pass") == good
    mutations = []
    for name, mutate in [
        ("missing_metric_code", lambda x: x.pop("metricCode")),
        ("nonnumeric_metric", lambda x: x["metricValue"].update(value="not-a-number")),
        ("invalid_result", lambda x: x["result"].update(value="certainly-good")),
        ("missing_target", lambda x: x.pop("refEntity")),
        ("fake_hash", lambda x: x["evidenceHash"].update(value="sha256:illustrative")),
        ("unjustified_source_verification", lambda x: x["evidenceIntegrityStatus"].update(value="verified")),
        ("malformed_relationship", lambda x: x["refEntity"].update(object="D1")),
        ("no_threshold", lambda x: [x.pop(k, None) for k in ["thresholdMin", "thresholdMax"]]),
    ]:
        bad = copy.deepcopy(entities[0]); mutate(bad)
        rejected = bool(list(validator.iter_errors(bad)))
        assert rejected, name
        mutations.append({"mutation": name, "rejected": rejected})
    write_json(output / "data/normalized_evidence.jsonld", {"@context": CONTEXT, "@graph": list(entities)})
    write_json(output / "data/anonymized_source_records.json", list(records))
    write_json(output / "data/identifier_mapping.json", [
        {"source_id": r["id"], "context": r["contextWindow"], "revised_id": entity["id"]}
        for r, entity in zip(records, entities)])
    write_json(output / "schemas/assessment.schema.json", schema)
    write_json(output / "contexts/data-quality-context.jsonld", {"@context": CONTEXT})
    (output / "schemas/quality-profile.shacl.ttl").write_text(SHAPES)
    (output / "queries/low_headroom.rq").parent.mkdir(parents=True, exist_ok=True)
    (output / "queries/low_headroom.rq").write_text(QUERY)

    ngsi_graph = Graph().parse(data=json.dumps({"@context": CONTEXT, "@graph": list(entities)}), format="json-ld")
    assert len(set(ngsi_graph.subjects(RDF.type, DQ.DataQualityAssessment))) == len(entities)
    for entity in entities:
        node = URIRef(entity["id"])
        value_nodes = list(ngsi_graph.objects(node, DQ.metricValue))
        assert len(value_nodes) == 1
        values = list(ngsi_graph.objects(value_nodes[0], NGSI.hasValue))
        assert len(values) == 1 and float(values[0]) == entity["metricValue"]["value"]
        target_nodes = list(ngsi_graph.objects(node, DQ.refEntity))
        assert len(target_nodes) == 1
        targets = list(ngsi_graph.objects(target_nodes[0], NGSI.hasObject))
        assert targets == [URIRef(entity["refEntity"]["object"])]
    rdf_graph = rdf_export(records, entities)
    rdf_graph.serialize(destination=str(output / "data/dqv_prov_dcat.ttl"), format="turtle")
    rdf_graph.serialize(destination=str(output / "data/dqv_prov_dcat.jsonld"), format="json-ld")
    roundtrip = Graph().parse(output / "data/dqv_prov_dcat.jsonld", format="json-ld")
    assert isomorphic(rdf_graph, roundtrip)
    shapes = Graph().parse(data=SHAPES, format="turtle")
    conforms, report, report_text = shacl_validate(rdf_graph, shacl_graph=shapes, inference="none")
    assert conforms, report_text
    (output / "results/shacl_report.txt").write_text(report_text)
    malformed = Graph()
    for triple in rdf_graph:
        malformed.add(triple)
    first = URIRef(records[0]["id"])
    malformed.remove((first, PROV.wasDerivedFrom, None))
    bad_conforms, _, bad_report = shacl_validate(malformed, shacl_graph=shapes, inference="none")
    assert not bad_conforms
    (output / "results/shacl_negative_report.txt").write_text(bad_report)
    rows = [{"measurement": str(row[0]), "value": float(row[1]), "limit": float(row[2])}
            for row in rdf_graph.query(QUERY)]
    assert len(rows) == 2
    write_json(output / "results/low_headroom_query.json", rows)
    ratios = [r["metricValue"] / r["thresholdMax"] for r in records
              if r["metricCode"] == "expanded_uncertainty_at_limit"]
    return {
        "assertion_count": len(entities), "json_schema_valid": len(entities),
        "original_distinct_identifiers": len(id_counts), "revised_distinct_identifiers": len(entities),
        "colliding_identifier_values_repaired": sum(v > 1 for v in id_counts.values()),
        "recomputed_within_supplied_thresholds": sum(recomputed),
        "source_reports_authenticated": False, "source_report_hashes_available": False,
        "missing_original_report_hashes": len(entities),
        "json_schema_negative_mutations": mutations,
        "ngsi_jsonld_rdf_triples": len(ngsi_graph),
        "ngsi_entities_metric_values_and_targets_preserved": len(entities),
        "between_sensor_group_records": sum(r["metricCode"] == "u_between_sensors" for r in records),
        "rdf_export_triples": len(rdf_graph), "rdf_roundtrip_isomorphic": True,
        "shacl_valid": bool(conforms), "missing_provenance_negative_rejected": not bool(bad_conforms),
        "sparql_low_headroom_matches": len(rows),
        "expanded_uncertainty_ratios": {"mean": statistics.mean(ratios), "median": statistics.median(ratios), "max": max(ratios)},
        "scope": "Application-defined schema and SHACL checks; not third-party certification or full ontology conformance",
    }

def evaluate_case(case):
    completeness = min(1.0, max(0.0, case["received"] / POLICY["expected_samples"]))
    freshness = math.exp(-max(0.0, case["age"] - POLICY["freshness_grace_seconds"]) / POLICY["freshness_decay_seconds"])
    weights = POLICY["weights"]
    score = weights["completeness"] * completeness + weights["freshness"] * freshness + weights["schema"] * case["schema"]
    gates = {"completeness": completeness >= POLICY["gate_min_completeness"], "age": 0 <= case["age"] <= POLICY["gate_max_age_seconds"],
             "schema": case["schema"] == POLICY["gate_schema_score"], "calibration": case["calibration"] is True,
             "source_integrity": case["integrity"] == "verified-test-fixture",
             "unit": case["unit"] == POLICY["unit"], "firmware": case["firmware"] == POLICY["firmware"],
             "scope": case["scope"] == POLICY["scope"], "hardware_status": not case["hardware_fault"],
             "outlier": not case["outlier"], "score": score >= POLICY["minimum_aggregate"],
             "access_authorized": case["access_authorized"] is True}
    failed = [k for k, v in gates.items() if not v]
    return {**case, "completeness": completeness, "freshness": freshness, "score": score,
            "accepted": not failed, "failed_gates": failed,
            "action": "accept" if not failed else "quarantine",
            "incident": None if not failed else "urn:revision:incident:" + case["name"]}

def scenario_checks(output):
    # Feed a measured synthetic detector output into the corresponding rule test.
    values = [40 + 0.2 * math.sin(i / 5) for i in range(60)]
    values[30] = 1000.0
    median = statistics.median(values)
    mad = statistics.median(abs(v - median) for v in values)
    indices = [i for i, v in enumerate(values) if abs(v - median) > 6 * 1.4826 * mad]
    assert indices == [30]
    healthy = {"name": "healthy", "received": 58, "age": 7, "schema": 1.0,
               "calibration": True, "integrity": "verified-test-fixture", "unit": "synthetic-S01",
               "firmware": "v1", "scope": "site-A", "hardware_fault": False, "outlier": False,
               "synthetic": True, "access_authorized": True,
               "security_scope": "authorization is an assumed Boolean fixture; no TLS/identity/policy engine is tested"}
    cases = [healthy]
    for name, changes in [
        ("stale", {"age": 150}), ("packet_loss", {"received": 45}),
        ("schema_failure", {"schema": 0.9}),
        ("hardware_failure", {"hardware_fault": True}),
        ("outlier", {"outlier": bool(indices)}),
        ("expired_calibration", {"calibration": False}),
        ("firmware_changed", {"firmware": "v2"}),
        ("different_unit", {"unit": "synthetic-S02"}),
        ("different_site", {"scope": "site-B"}),
        ("missing_source_evidence", {"integrity": "unknown"}),
        ("tampered_evidence", {"integrity": "digest-mismatch"}),
    ]:
        cases.append({**healthy, "name": name, **changes})
    results = [evaluate_case(c) for c in cases]
    assert results[0]["accepted"] and math.isclose(results[0]["score"], 59 / 60)
    assert sum(x["accepted"] for x in results) == 1
    results[5]["outlier_detector"] = {"method": "absolute deviation > 6 x 1.4826 x median absolute deviation",
                                      "detected_indices": indices, "median": median, "mad": mad}
    write_json(output / "data/synthetic_policy.json", POLICY)
    write_json(output / "results/scenario_results.json", results)
    return {"cases": len(results), "healthy_accepted": 1, "adverse_quarantined": len(results) - 1,
            "healthy_score": results[0]["score"], "outlier_detected_index": indices,
            "scope": "Deterministic synthetic rule tests, not estimated false-positive/false-negative rates"}

def fixture_key():
    # A public deterministic TEST key, never use for real evidence or identity.
    return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b"PUBLIC TEST FIXTURE ONLY DQ revision 2026").digest())

def crypto_checks(output):
    key = fixture_key()
    public = key.public_key()
    message = canonical_bytes({"synthetic": True, "purpose": "byte-integrity-demonstration", "score": 59 / 60})
    signature = key.sign(message)
    public.verify(signature, message)
    tampered = message.replace(b"true", b"false")
    rejected = False
    try:
        public.verify(signature, tampered)
    except InvalidSignature:
        rejected = True
    assert rejected
    result = {"public_test_key_hex": public.public_bytes(Encoding.Raw, PublicFormat.Raw).hex(),
              "message_sha256": sha(message), "signature_hex": signature.hex(),
              "original_signature_verified": True, "tampered_payload_rejected": rejected,
              "source_identity_authenticated": False,
              "scope": "Public test key; authenticates no laboratory, certificate, organization, or live device"}
    write_json(output / "results/signature_demonstration.json", result)
    (output / "data/synthetic_signed_message.json").write_bytes(message)
    return result

def observation(i):
    return {"id": f"urn:ngsi-ld:AirQualityObserved:synthetic:{i:06d}", "type": "AirQualityObserved",
            "NO2": {"type": "Property", "value": round(40 + 0.2 * math.sin(i / 5), 5), "unitCode": "GQ"},
            "sequence": prop(i), "refDevice": rel("urn:ngsi-ld:Device:synthetic-S01")}

def runtime_assessment(index, window_size, data_digest):
    return {"id": f"urn:ngsi-ld:DataQualityAssessment:synthetic:{index:06d}", "type": "DataQualityAssessment",
            "refEntity": rel("urn:ngsi-ld:Device:synthetic-S01"), "synthetic": prop(True),
            "windowStart": prop(index * window_size), "windowEnd": prop((index + 1) * window_size),
            "completeness": prop(1.0), "freshness": prop(1.0), "schemaScore": prop(1.0),
            "sampleCount": prop(window_size), "expectedCount": prop(window_size),
            "policyVersion": prop(f"urn:revision:policy:benchmark:window-{window_size}s:1"), "qualityScore": prop(1.0),
            "evidenceHash": prop("sha256:" + data_digest), "evidenceHashScope": prop("serialized observations in this synthetic window"),
            "evidenceIntegrityStatus": prop("verified-test-fixture"), "result": prop("pass")}

def workload(mode, observations, key):
    window_size = 1 if mode == "per_observation" else 60
    total_bytes = len(canonical_bytes({"@context": CONTEXT}))
    hashes = signatures = assessments = 0
    start = time.perf_counter_ns()
    for start_at in range(0, len(observations), window_size):
        group = observations[start_at:start_at + window_size]
        if mode == "baseline":
            for original in group:
                total_bytes += len(canonical_bytes(original)) + 1
            continue
        index = start_at // window_size
        digest = hashlib.sha256()
        for original in group:
            # This is an archive assembly benchmark: the closed-window result is
            # appended retrospectively, not asserted to be available before closure.
            o = dict(original)
            o["NO2"] = {**original["NO2"], "qualityScore": prop(1.0), "qualityLevel": prop("synthetic-valid"),
                        "hasQualityAssessment": rel(f"urn:ngsi-ld:DataQualityAssessment:synthetic:{index:06d}")}
            payload = canonical_bytes(o) + b"\n"
            total_bytes += len(payload)
            digest.update(payload)
        hashes += 1
        assessment = runtime_assessment(index, window_size, digest.hexdigest())
        assessment_bytes = canonical_bytes(assessment)
        signature = key.sign(assessment_bytes)
        total_bytes += len(assessment_bytes) + len(signature.hex()) + 1
        signatures += 1
        assessments += 1
    elapsed = (time.perf_counter_ns() - start) / 1e6
    return {"mode": mode, "observations": len(observations), "elapsed_ms": elapsed,
            "serialized_bytes": total_bytes, "assessments": assessments, "sha256_digests": hashes,
            "ed25519_signatures": signatures}

def benchmark(output, n=3600, repetitions=7):
    assert n % 60 == 0
    observations = [observation(i) for i in range(n)]
    key = fixture_key()
    modes = ["baseline", "per_observation", "window_60s"]
    for mode in modes:
        workload(mode, observations[:60], key)
    all_rows = []
    # Interleave modes to avoid measuring all of one mode in one thermal period.
    for r in range(repetitions):
        for mode in modes[r % 3:] + modes[:r % 3]:
            all_rows.append({"run": r + 1, **workload(mode, observations, key)})
    summary = []
    for mode in modes:
        rows = [r for r in all_rows if r["mode"] == mode]
        times = [r["elapsed_ms"] for r in rows]
        summary.append({"mode": mode, "observations": n, "repetitions": repetitions,
                        "median_ms": statistics.median(times), "min_ms": min(times), "max_ms": max(times),
                        "serialized_bytes": rows[0]["serialized_bytes"], "assessments": rows[0]["assessments"],
                        "sha256_digests": rows[0]["sha256_digests"], "ed25519_signatures": rows[0]["ed25519_signatures"]})
    with (output / "results/benchmark_raw.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0])); writer.writeheader(); writer.writerows(all_rows)
    write_json(output / "results/benchmark_summary.json", summary)
    return {"configuration": {"observations": n, "simulated_sampling_hz": 1, "simulated_duration_seconds": n,
                               "window_seconds": 60, "repetitions": repetitions, "warmup_observations_per_mode": 60,
                               "context_accounting": "one shared inline context counted once in each archive",
                               "scope": "In-memory serialization, SHA-256 and test-key Ed25519 only; no network, disk, database, query, subscription or connector timings",
                               "closed_window_delay": "Up to 60 seconds plus actual processing; retrospective archive scoring only"},
            "summary": summary}

def main():
    parser = argparse.ArgumentParser()
    bundled_input = HERE / "source/cen17660_evidence_input.json"
    parser.add_argument("--input", type=Path, default=bundled_input if bundled_input.exists() else
                        HERE.parent / "original/data/cen17660_evidence.jsonld")
    parser.add_argument("--output", type=Path, default=HERE / "rerun" if bundled_input.exists() else HERE / "package")
    parser.add_argument("--observations", type=int, default=3600)
    parser.add_argument("--repetitions", type=int, default=7)
    args = parser.parse_args()
    for folder in ["data", "schemas", "contexts", "queries", "results"]:
        (args.output / folder).mkdir(parents=True, exist_ok=True)
    versions = {}
    for name in ["rdflib", "pyshacl", "jsonschema", "cryptography"]:
        versions[name] = importlib.metadata.version(name)
    environment = {"python": sys.version.split()[0], "platform": platform.platform(),
                   "processor": platform.processor(), "logical_cpus_reported": os.cpu_count(), "versions": versions,
                   "execution": "single process; wall-clock measurements in shared sandbox; workload interleaved"}
    results = {"environment": environment, "source_validation": check_sources(args.input, args.output),
               "scenarios": scenario_checks(args.output), "cryptographic_test": crypto_checks(args.output),
               "benchmark": benchmark(args.output, args.observations, args.repetitions),
               "real_ngsi_ld_broker_executed": False, "data_space_connector_executed": False,
               "municipal_deployment_evaluated": False}
    write_json(args.output / "results/validation_summary.json", results)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
