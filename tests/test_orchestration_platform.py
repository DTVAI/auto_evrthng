import unittest
from app.domains import orchestration as o, platform as t


class ToolsTest(unittest.TestCase):
    def test_samples(self):
        for module in (o, t):
            self.assertEqual(module.TOOL_IDS, set(module.SAMPLES))
            for name, payload in module.SAMPLES.items():
                with self.subTest(name=name):
                    result = module.run(name, payload)
                    self.assertNotEqual(result["status"], "EXCEPTION", result)
                    self.assertEqual(
                        set(result),
                        {
                            "status",
                            "summary",
                            "data",
                            "checks",
                            "artifacts",
                            "warnings",
                        },
                    )

    def test_cycle_and_unknown_dependencies(self):
        for tasks in (
            [{"id": "a", "depends_on": ["b"]}, {"id": "b", "depends_on": ["a"]}],
            [{"id": "a", "depends_on": ["missing"]}],
        ):
            self.assertEqual(
                o.run("O02", {"target_date": "2027-01-01", "tasks": tasks})["status"],
                "EXCEPTION",
            )

    def test_transitive_impact_and_conditional_form(self):
        self.assertEqual(
            o.run(
                "O05",
                {
                    "changed": ["a"],
                    "dependencies": {"a": ["b"], "b": ["c"], "c": ["a"]},
                },
            )["data"]["affected"],
            ["b", "c"],
        )
        result = o.run(
            "O04",
            {
                "fields": [
                    {"name": "address", "when": {"field": "remote", "equals": True}}
                ],
                "facts": {},
            },
        )
        self.assertEqual(result["data"]["unknown_conditions"], ["address"])
        self.assertEqual(result["status"], "NEEDS_DATA")

    def test_authority_and_stale_approval(self):
        payload = dict(t.SAMPLES["T02"])
        payload["scope"] = "other"
        self.assertEqual(t.run("T02", payload)["status"], "NEEDS_DECISION")
        payload = dict(t.SAMPLES["T02"])
        payload["approval"] = {**payload["approval"], "scope_hash": "old"}
        self.assertEqual(t.run("T02", payload)["status"], "NEEDS_DECISION")
        self.assertEqual(
            t.run("T02", {"rule": payload["rule"]})["status"], "NEEDS_DATA"
        )
        payload = dict(t.SAMPLES["T02"])
        payload["action"] = "unknown"
        payload["approval"] = {**payload["approval"], "action": "unknown"}
        self.assertEqual(t.run("T02", payload)["status"], "NEEDS_DECISION")

    def test_ambiguous_execution_never_retry(self):
        for state in ("UNKNOWN", "RUNNING", "TIMEOUT", "unexpected"):
            result = t.run(
                "T03",
                {
                    "now": "2027-01-01T12:00:00",
                    "timer_at": "2027-01-01T11:00:00",
                    "external_state": state,
                },
            )
            self.assertEqual(result["data"]["external_state"], "UNKNOWN")
            self.assertIn("nicht erneut senden", result["data"]["next_step"])

    def test_bad_manifest_and_unverified_result(self):
        self.assertEqual(
            t.run("T10", {"contents": {"db": "abc"}, "manifest": {"db": "wrong"}})[
                "status"
            ],
            "EXCEPTION",
        )
        self.assertEqual(
            t.run("T06", {"expected": {"id": "a"}, "observed": {"id": "a"}})["status"],
            "NEEDS_DATA",
        )
        self.assertEqual(
            t.run(
                "T06",
                {
                    "expected": {"id": "a"},
                    "observed": {"id": "b"},
                    "evidence": {
                        "independent": True,
                        "source": "target",
                        "reference": "1",
                    },
                },
            )["status"],
            "EXCEPTION",
        )

    def test_rule_and_document_injection_rejected(self):
        self.assertEqual(
            o.run(
                "O12",
                {
                    "rule": {"field": "x", "op": "eval", "value": "1"},
                    "cases": [{"x": 1}],
                },
            )["status"],
            "EXCEPTION",
        )
        self.assertEqual(
            t.run(
                "T07",
                {
                    "template": "{name.__class__}",
                    "version": "1",
                    "approved": True,
                    "allowed_fields": ["name"],
                    "facts": {"name": "x"},
                },
            )["status"],
            "EXCEPTION",
        )

    def test_bitemporal_revision_selection(self):
        facts = [
            {
                "field": "location",
                "value": "Berlin",
                "valid_from": "2027-01-01",
                "observed_at": "2027-01-01",
                "source": "s",
            },
            {
                "field": "location",
                "value": "Bonn",
                "valid_from": "2027-01-01",
                "observed_at": "2027-02-01",
                "source": "s",
            },
            {
                "field": "location",
                "value": "Kiel",
                "valid_from": "2027-01-01",
                "observed_at": "2027-04-01",
                "source": "s",
            },
        ]
        result = t.run(
            "T01", {"valid_at": "2027-03-01", "known_at": "2027-03-01", "facts": facts}
        )
        self.assertEqual(result["data"]["facts"]["location"]["value"], "Bonn")
        self.assertEqual(len(result["data"]["facts"]), 1)
        facts.append({**facts[1], "value": "Hamburg"})
        self.assertEqual(
            t.run(
                "T01",
                {"valid_at": "2027-03-01", "known_at": "2027-03-01", "facts": facts},
            )["status"],
            "NEEDS_DECISION",
        )

    def test_backward_dependencies_and_missing_duration(self):
        tasks = [
            {"id": "a", "duration_days": 3, "confirmed": True},
            {"id": "b", "duration_days": 2, "depends_on": ["a"], "confirmed": True},
            {"id": "c", "duration_days": 4, "depends_on": ["a"], "confirmed": True},
        ]
        result = o.run("O02", {"target_date": "2027-04-01", "tasks": tasks})
        schedule = {x["id"]: x for x in result["data"]["schedule"]}
        self.assertEqual(schedule["a"]["start"], "2027-03-25")
        self.assertEqual(schedule["a"]["end"], schedule["c"]["start"])
        self.assertLessEqual(schedule["a"]["end"], schedule["b"]["start"])
        self.assertEqual(result["data"]["critical_path"], ["a", "c"])
        self.assertEqual(
            o.run(
                "O02",
                {
                    "target_date": "2027-04-01",
                    "tasks": [{"id": "a", "confirmed": True}],
                },
            )["status"],
            "NEEDS_DATA",
        )

    def test_complete_manifest_and_incomplete_inputs(self):
        self.assertEqual(
            t.run("T10", {"contents": {}, "manifest": {}})["status"], "NEEDS_DATA"
        )
        self.assertEqual(
            t.run(
                "T10",
                {
                    "contents": {"db": "abc", "extra": "x"},
                    "manifest": {"db": t.SAMPLES["T10"]["manifest"]["db"]},
                },
            )["status"],
            "EXCEPTION",
        )
        self.assertEqual(
            t.run(
                "T10",
                {"contents": {"db": "abc"}, "manifest": t.SAMPLES["T10"]["manifest"]},
            )["status"],
            "EXCEPTION",
        )
        self.assertFalse(t.run("T02", {"action": "review"})["data"]["authority"])
        self.assertEqual(o.run("O10", {})["status"], "NEEDS_DATA")

    def test_zero_skipped_failed_tests(self):
        self.assertEqual(t.run("T11", {})["status"], "NEEDS_DATA")
        self.assertEqual(
            t.run("T11", {"tests": [{"result": "skipped"}], "approval": True})[
                "status"
            ],
            "NEEDS_DECISION",
        )
        self.assertEqual(
            t.run("T11", {"tests": [{"result": "failed"}], "approval": True})["status"],
            "EXCEPTION",
        )


if __name__ == "__main__":
    unittest.main()
