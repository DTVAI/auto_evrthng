import copy
import unittest
from app.domains import personnel, staffing


class PersonnelStaffingTests(unittest.TestCase):
    def test_all_samples_execute(self):
        for module in (personnel, staffing):
            self.assertEqual(set(module.SAMPLES), module.TOOL_IDS)
            for tool, sample in module.SAMPLES.items():
                with self.subTest(tool=tool):
                    r = module.run(tool, copy.deepcopy(sample))
                    self.assertIn(r["status"], ("READY", "NEEDS_DECISION"))
                    self.assertEqual(
                        set(r),
                        {
                            "status",
                            "summary",
                            "data",
                            "checks",
                            "artifacts",
                            "warnings",
                        },
                    )

    def test_salary_rounding_and_conflict_per_person(self):
        p = copy.deepcopy(personnel.SAMPLES["P03"])
        p["people"].append({"person_id": "P2", "old": "100", "current": "99"})
        r = personnel.run("P03", p)
        self.assertEqual(r["data"]["people"][0]["new"], "3062.03")
        self.assertFalse(r["data"]["people"][0]["conflict"])
        self.assertTrue(r["data"]["people"][1]["conflict"])

    def test_salary_scope_and_manual_mode(self):
        p = copy.deepcopy(personnel.SAMPLES["P03"])
        first = personnel.run("P03", p)["data"]["people"][0]
        p["people"][0]["approval"] = {"by": "HR", "scope_hash": first["scope_hash"]}
        self.assertEqual(personnel.run("P03", p)["status"], "READY")
        p["currency"] = "USD"
        self.assertEqual(personnel.run("P03", p)["status"], "NEEDS_DECISION")
        p["mode"] = "manual"
        p["people"][0]["new"] = "3000.005"
        self.assertEqual(personnel.run("P03", p)["data"]["people"][0]["new"], "3000.01")
        p["people"].append(copy.deepcopy(p["people"][0]))
        self.assertTrue(
            all(row["conflict"] for row in personnel.run("P03", p)["data"]["people"])
        )

    def test_hours_expiry_and_bounds(self):
        p = copy.deepcopy(personnel.SAMPLES["P02"])
        self.assertEqual(
            personnel.run("P02", p)["data"]["expiry_task"]["due_date"], "2026-06-30"
        )
        p.pop("valid_to")
        self.assertEqual(personnel.run("P02", p)["status"], "NEEDS_DATA")
        p["model"] = "unbefristet"
        p["valid_to"] = "2026-06-30"
        self.assertEqual(personnel.run("P02", p)["status"], "NEEDS_DATA")
        p.pop("valid_to")
        p["new"] = "169"
        self.assertEqual(personnel.run("P02", p)["status"], "NEEDS_DATA")

    def test_offboarding_requires_scoped_attestations(self):
        p = copy.deepcopy(personnel.SAMPLES["P15"])
        p["tasks"][0]["confirmed"] = True
        r = personnel.run("P15", p)
        self.assertEqual(r["status"], "NEEDS_DECISION")
        p["decision_evidence"]["scope_hash"] = r["data"]["decision_scope_hash"]
        p["tasks"][0].update(confirmed_by="HR", evidence_id="E2")
        self.assertEqual(personnel.run("P15", p)["status"], "READY")
        p["end_date"] = "2027-01-01"
        self.assertEqual(personnel.run("P15", p)["status"], "NEEDS_DECISION")

    def test_contract_line_diff(self):
        r = personnel.run("P17", personnel.SAMPLES["P17"])
        self.assertIn("-40 Stunden", r["data"]["diff"])
        self.assertIn("+30 Stunden", r["data"]["diff"])

    def test_document_return_evidence(self):
        p = copy.deepcopy(personnel.SAMPLES["P06"])
        p["return_evidence"].update(
            method="verified_signature", evidence_id="E1", version="2"
        )
        self.assertEqual(personnel.run("P06", p)["status"], "NEEDS_DECISION")
        p["return_evidence"]["version"] = "1"
        self.assertEqual(personnel.run("P06", p)["status"], "READY")
        p["return_evidence"]["method"] = "ocr"
        self.assertEqual(personnel.run("P06", p)["status"], "NEEDS_DECISION")

    def test_period_overlap(self):
        p = copy.deepcopy(personnel.SAMPLES["P08"])
        p["periods"].append({"start": "2026-06-30", "end": "2026-07-01"})
        self.assertEqual(personnel.run("P08", p)["status"], "NEEDS_DECISION")

    def test_invoice_rounding_duplicates_and_lines(self):
        p = copy.deepcopy(staffing.SAMPLES["A06"])
        p["invoice_lines"][0].update(hours="1", rate="1.005", amount="1.01")
        p["confirmed_lines"][0].update(hours="1", rate="1.005")
        self.assertEqual(staffing.run("A06", p)["status"], "READY")
        p["existing_invoices"] = [{"supplier": "D1", "invoice_number": "I1"}]
        self.assertEqual(staffing.run("A06", p)["status"], "NEEDS_DECISION")
        p["existing_invoices"] = []
        p["invoice_lines"].append(copy.deepcopy(p["invoice_lines"][0]))
        self.assertEqual(staffing.run("A06", p)["status"], "NEEDS_DATA")

    def test_missing_and_template_gate(self):
        self.assertEqual(staffing.run("A01", {})["status"], "NEEDS_DATA")
        p = copy.deepcopy(personnel.SAMPLES["P05"])
        p["fields"].pop("name")
        self.assertEqual(personnel.run("P05", p)["status"], "NEEDS_DATA")

    def test_approval_bound_to_scope(self):
        p = copy.deepcopy(personnel.SAMPLES["P01"])
        h = personnel.run("P01", p)["data"]["scope_hash"]
        p["approval"] = {"by": "HR", "scope_hash": h}
        self.assertEqual(personnel.run("P01", p)["status"], "READY")
        p["new"] = "4201.00"
        self.assertEqual(personnel.run("P01", p)["status"], "NEEDS_DECISION")


if __name__ == "__main__":
    unittest.main()
