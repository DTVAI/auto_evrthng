import unittest
from app.domains import communication as m, recruiting as r


class Workflows(unittest.TestCase):
    def test_samples(self):
        for module in (m, r):
            self.assertEqual(module.TOOL_IDS, set(module.SAMPLES))
            for tool, payload in module.SAMPLES.items():
                with self.subTest(tool=tool):
                    result = module.run(tool, payload)
                    self.assertEqual(result["status"], "READY", result)
                    self.assertIsInstance(result["data"], dict)
                    self.assertIsInstance(result["checks"], list)
                    self.assertIsInstance(result["artifacts"], list)

    def test_ndr_overrides_rule_and_archive(self):
        p = {
            "message": {
                "id": "1",
                "sender": "system",
                "subject": "NDR",
                "body": "Fehler",
                "reference": "send1",
            },
            "rules": [{"sender": "system", "approved": True, "version": "1"}],
        }
        self.assertEqual(m.run("M01", p)["status"], "EXCEPTION")
        self.assertEqual(
            m.run(
                "M02",
                {
                    "message": p["message"],
                    "receipt": {"result": "success", "verified": True},
                    "retention": {"approved": True, "version": "1"},
                },
            )["status"],
            "EXCEPTION",
        )

    def test_duplicates_preserve_new_question(self):
        result = m.run(
            "M03",
            {
                "messages": [
                    {
                        "id": "1",
                        "mailbox": "hr",
                        "internet_id": "x",
                        "body": "Hallo",
                        "questions": ["A"],
                    },
                    {
                        "id": "2",
                        "mailbox": "hr",
                        "internet_id": "x",
                        "body": "Hallo B?",
                        "questions": ["B"],
                    },
                ]
            },
        )
        self.assertIsNone(result["data"]["messages"][1]["duplicate_of"])
        self.assertEqual(result["data"]["messages"][1]["questions"], ["B"])

    def test_partial_and_contradictory_answers(self):
        p = {
            "case_id": "c",
            "questions": [{"id": "q", "text": "Wann?"}, {"id": "q2", "text": "Wo?"}],
            "answers": [
                {
                    "case_id": "c",
                    "question_id": "q",
                    "source": "a",
                    "identity_confirmed": True,
                    "state": "answered",
                    "value": "A",
                },
                {
                    "case_id": "c",
                    "question_id": "q",
                    "source": "b",
                    "identity_confirmed": True,
                    "state": "answered",
                    "value": "B",
                },
                {
                    "case_id": "c",
                    "question_id": "q2",
                    "source": "c",
                    "identity_confirmed": True,
                    "state": "partial",
                },
            ],
        }
        states = [x["state"] for x in m.run("M05", p)["data"]["questions"]]
        self.assertEqual(states, ["contradictory", "partial"])

    def test_draft_freshness(self):
        draft = m.run("M07", m.SAMPLES["M07"])["data"]
        snapshot = draft["snapshot"].copy()
        snapshot["template"] = {**snapshot["template"], "version": "2"}
        self.assertEqual(
            m.run(
                "M08",
                {"snapshot_hash": draft["snapshot_hash"], "current_snapshot": snapshot},
            )["status"],
            "NEEDS_DECISION",
        )

    def test_access_search(self):
        p = {
            "records": [
                {"case_id": "1", "scope": "Nord"},
                {"case_id": "1", "scope": "Süd"},
            ],
            "search_type": "case_id",
            "query": "1",
            "authorized_scopes": ["Nord"],
            "purpose": "Arbeit",
        }
        self.assertEqual(len(m.run("M10", p)["data"]["matches"]), 1)

    def test_same_source_id_with_changed_content_is_conflict(self):
        result = m.run(
            "M03",
            {
                "messages": [
                    {"id": "1", "mailbox": "hr", "body": "Alt", "questions": ["A"]},
                    {"id": "1", "mailbox": "hr", "body": "Neu", "questions": ["B"]},
                ]
            },
        )
        self.assertEqual(result["status"], "NEEDS_DECISION")
        self.assertTrue(result["data"]["messages"][1]["identity_conflict"])
        self.assertIsNone(result["data"]["messages"][1]["duplicate_of"])
        self.assertEqual(result["data"]["messages"][1]["questions"], ["B"])

    def test_known_answer_is_not_externally_delivered(self):
        p = {
            "case_id": "c",
            "questions": [
                {
                    "id": "q",
                    "text": "Wann?",
                    "audience": "external",
                    "recipient": "a@example.org",
                }
            ],
            "answers": [
                {
                    "question_id": "q",
                    "case_id": "c",
                    "source": "notiz",
                    "direction": "internal",
                    "state": "answered",
                    "value": "morgen",
                }
            ],
        }
        item = m.run("M05", p)["data"]["questions"][0]
        self.assertEqual(
            (item["knowledge_state"], item["outbound_state"], item["state"]),
            ("answered", "not_delivered", "open"),
        )
        p["answers"].append(
            {
                "question_id": "q",
                "case_id": "c",
                "source": "entwurf",
                "direction": "outbound",
                "state": "answered",
                "value": "morgen",
                "recipient": "a@example.org",
                "delivery_evidence": {"source": "receipt", "delivered": True},
            }
        )
        self.assertEqual(m.run("M05", p)["data"]["questions"][0]["state"], "answered")
        p["answers"][1]["recipient"] = "wrong@example.org"
        self.assertEqual(m.run("M05", p)["data"]["questions"][0]["state"], "open")

    def test_unverified_inbound_identity_does_not_answer(self):
        p = {
            "case_id": "c",
            "questions": [{"id": "q", "text": "Wann?"}],
            "answers": [
                {
                    "question_id": "q",
                    "case_id": "c",
                    "source": "m1",
                    "state": "answered",
                    "value": "morgen",
                }
            ],
        }
        self.assertEqual(m.run("M05", p)["data"]["questions"][0]["state"], "open")

    def test_commitment_requires_specific_evidence(self):
        p = {**m.SAMPLES["M06"], "evidence": {}}
        self.assertFalse(m.run("M06", p)["data"]["fulfilled"])
        p["evidence"] = {"source": "m2", "verified": True, "fulfillment": "anderes"}
        self.assertFalse(m.run("M06", p)["data"]["fulfilled"])
        p["evidence"]["fulfillment"] = p["fulfillment"]
        self.assertTrue(m.run("M06", p)["data"]["fulfilled"])

    def test_dst_and_wrong_recipient(self):
        p = {
            **r.SAMPLES["R10"],
            "start": "2026-10-25T02:15:00+02:00",
            "end": "2026-10-25T02:45:00+02:00",
            "busy": [
                {
                    "start": "2026-10-25T02:15:00+01:00",
                    "end": "2026-10-25T02:45:00+01:00",
                }
            ],
        }
        self.assertEqual(r.run("R10", p)["status"], "READY")
        p["recipients"] = [{**x, "application_id": "other"} for x in p["recipients"]]
        self.assertEqual(r.run("R10", p)["status"], "NEEDS_DECISION")
        p["busy"] = [{"start": "2026-10-25T02:15:00", "end": "2026-10-25T02:45:00"}]
        self.assertEqual(r.run("R10", p)["status"], "NEEDS_DATA")

    def test_money_and_capacity(self):
        p = {**r.SAMPLES["R01"], "requested": "NaN"}
        self.assertEqual(r.run("R01", p)["status"], "NEEDS_DATA")
        p = {**r.SAMPLES["R02"], "price": "900"}
        self.assertEqual(r.run("R02", p)["status"], "NEEDS_DECISION")

    def test_identity_ambiguity(self):
        p = {**r.SAMPLES["R05"], "candidates": r.SAMPLES["R05"]["candidates"] * 2}
        self.assertEqual(r.run("R05", p)["status"], "NEEDS_DECISION")

    def test_collision_and_offset(self):
        p = {
            **r.SAMPLES["R10"],
            "busy": [
                {
                    "start": "2026-11-01T09:30:00+00:00",
                    "end": "2026-11-01T10:30:00+00:00",
                }
            ],
        }
        self.assertEqual(r.run("R10", p)["status"], "NEEDS_DECISION")
        p["start"] = "2026-11-01T10:00:00"
        self.assertEqual(r.run("R10", p)["status"], "NEEDS_DATA")

    def test_start_readiness_requires_actual_evidence(self):
        p = {
            **r.SAMPLES["R13"],
            "checklist": {
                **r.SAMPLES["R13"]["checklist"],
                "it": {
                    "confirmed": False,
                    "evidence": "Ticket beantragt",
                    "revision": "1",
                },
            },
        }
        self.assertFalse(r.run("R13", p)["data"]["ready_for_start"])

    def test_change_requires_separate_approval(self):
        p = {**r.SAMPLES["R14"], "candidate_consent": None}
        result = r.run("R14", p)
        self.assertEqual(result["status"], "NEEDS_DECISION")
        self.assertEqual(result["data"]["effective_date"], p["old_date"])

    def test_profile_requires_identity(self):
        self.assertEqual(
            r.run("R15", {**r.SAMPLES["R15"], "identity_confirmed": False})["status"],
            "NEEDS_DECISION",
        )


if __name__ == "__main__":
    unittest.main()
