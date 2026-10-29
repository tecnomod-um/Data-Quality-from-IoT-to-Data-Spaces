"""Offline failure-path tests; fake responses are never real testbed evidence."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("toolbox_probe", ROOT / "probe.py")
probe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = probe
spec.loader.exec_module(probe)


class FakeBroker:
    kind = "offline_test_double"

    def __init__(self, context, failure=None):
        self.context, self.failure = context, failure
        self.entities, self.deleted, self.methods = {}, [], []
        self.posts = 0

    def __call__(self, method, url, headers, body):
        self.methods.append(method)
        parsed = urlsplit(url)
        if parsed.hostname == "context.example.org":
            if "Authorization" in headers:
                raise AssertionError("Credential leaked to context host")
            return probe.Reply(200, probe.encode({"@context": self.context}))
        if self.failure == "unavailable":
            return probe.Reply(503, b"connection timeout", "text/plain")
        path = parsed.path.split("/ngsi-ld/v1", 1)[1]
        if method == "POST":
            self.posts += 1
            entity = json.loads(body)
            if self.failure == "conflict" and self.posts == 2:
                return probe.Reply(409, b"{}")
            if self.failure == "lost_create" and self.posts == 2:
                self.entities[entity["id"]] = entity
                raise TimeoutError("Deliberately unknown create outcome")
            self.entities[entity["id"]] = entity
            return probe.Reply(201, b"")
        if path.startswith("/entities/"):
            eid = unquote(path.removeprefix("/entities/"))
            if method == "DELETE":
                if eid not in self.entities:
                    raise AssertionError("Attempt to delete an unknown resource")
                self.deleted.append(eid)
                del self.entities[eid]
                return probe.Reply(204, b"")
            if eid not in self.entities:
                return probe.Reply(404, b"{}")
            entity = json.loads(json.dumps(self.entities[eid]))
            if self.failure == "ownership_changed":
                entity["testRun"]["value"] = "another-run"
            if self.failure == "measurement_tampered" and entity["type"] == "AirQualityObserved":
                entity["NO2"]["value"] = 9999
            return probe.Reply(200, probe.encode(entity))
        query = parse_qs(parsed.query)
        selected = [self.entities[eid] for eid in query.get("id", [""])[0].split(",")
                    if eid in self.entities]
        if "q" in query:
            if self.failure == "unsupported_query":
                return probe.Reply(400, b"{\"detail\":\"unsupported\"}")
            selected = [entity for entity in selected
                        if entity["NO2"]["qualityScore"]["value"] >= 0.98
                        and entity["NO2"]["qualityLevel"]["value"] == "valid"]
        selected = json.loads(json.dumps(selected))
        if self.failure == "measurement_tampered":
            for entity in selected:
                if entity["type"] == "AirQualityObserved":
                    entity["NO2"]["value"] = 9999
        return probe.Reply(200, probe.encode(selected))


class SafetyAndEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = probe.load_config(ROOT / "config.example.json")
        self.config.update(context_url="https://context.example.org/context.jsonld",
                           tenant="dq_replication", repetitions=2)
        self.context = json.loads((ROOT / "context.jsonld").read_text())["@context"]

    def run_harness(self, mode, failure=None):
        fake = FakeBroker(self.context, failure)
        output = Path(self.temp.name) / "capture"
        harness = probe.Harness(self.config, output, "private-producer-token",
                                "private-consumer-token", fake)
        with patch.object(probe.time, "sleep"):
            result = harness.run(mode)
        self.assertNotIn("private-producer-token", (output / "run_result.json").read_text())
        self.assertNotIn("private-consumer-token", (output / "run_result.json").read_text())
        return fake, result

    def test_plan_makes_no_requests(self):
        fake, result = self.run_harness("plan")
        self.assertEqual(fake.methods, [])
        self.assertFalse(result["successful_network_fixture_roundtrip"])

    def test_probe_captures_unavailable_status_without_mutation(self):
        fake, result = self.run_harness("probe", "unavailable")
        self.assertEqual(fake.methods, ["GET"])
        self.assertEqual(result["probe_http_status"], 503)
        self.assertFalse(result["quality_query_verified"])

    def test_success_cleans_exactly_created_ids_and_is_not_live_evidence(self):
        fake, result = self.run_harness("measure")
        self.assertEqual(result["status"], "fixture_checks_passed")
        self.assertEqual(len(fake.deleted), 6)
        self.assertEqual(fake.entities, {})
        self.assertTrue(result["cleanup_complete"])
        self.assertFalse(result["successful_network_fixture_roundtrip"])
        self.assertEqual(result["transport_kind"], "offline_test_double")
        self.assertEqual([row["decision"] for row in result["consumer_decisions"]].count("accept"), 1)

    def test_conflict_does_not_delete_unowned_id(self):
        fake, result = self.run_harness("measure", "conflict")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(fake.deleted), 1)
        self.assertEqual(len(result["ownership_receipts"]), 1)

    def test_uncertain_create_is_logged_and_not_deleted(self):
        fake, result = self.run_harness("measure", "lost_create")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(result["indeterminate_create_ids"]), 1)
        self.assertFalse(result["cleanup_complete"])
        self.assertEqual(len(fake.entities), 1)
        self.assertNotIn(result["indeterminate_create_ids"][0], fake.deleted)

    def test_changed_ownership_prevents_deletion(self):
        fake, result = self.run_harness("measure", "ownership_changed")
        self.assertFalse(result["cleanup_complete"])
        self.assertEqual(fake.deleted, [])
        self.assertEqual(len(fake.entities), 6)

    def test_unsupported_nested_query_is_failure_not_downgraded(self):
        fake, result = self.run_harness("measure", "unsupported_query")
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["quality_query_verified"])
        self.assertTrue(result["cleanup_complete"])
        self.assertEqual(len(fake.deleted), 6)

    def test_measurement_must_match_hashed_fixture_inputs(self):
        fake, result = self.run_harness("measure", "measurement_tampered")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure"], "consumer_decisions_differ_from_declared_fixture")
        self.assertFalse(result["successful_network_fixture_roundtrip"])
        self.assertTrue(result["cleanup_complete"])

    def test_redirect_handler_never_forwards_request(self):
        handler = probe.NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "", {},
                                                   "https://other.example.org/"))


if __name__ == "__main__":
    unittest.main()
