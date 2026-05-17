import unittest

from paper_ingest import auto_tag, extract_title_from_ocr, infer_domain, infer_paper_type, normalize_page_body, _summary_prompt


class PaperIngestPromptTests(unittest.TestCase):
    def test_extract_title_skips_bmj_boilerplate(self):
        ocr = """Open access

Protocol

# BMJ Open Effects of semaglutide on chronic kidney disease in patients with type 2 diabetes: rationale and design of a multicentre randomised controlled trial

Example Author

To cite: Example Author. Effects of semaglutide on chronic kidney disease in patients with type 2 diabetes: rationale and design of a multicentre randomised controlled trial. BMJ Open 2022.
"""
        self.assertEqual(
            extract_title_from_ocr(ocr),
            "Effects of semaglutide on chronic kidney disease in patients with type 2 diabetes: rationale and design of a multicentre randomised controlled trial",
        )

    def test_summary_prompt_separates_protocol_assumptions_from_results(self):
        prompt = _summary_prompt(
            "Methods and analysis The ABLATION trial is a prospective protocol.",
            {"title": "Open access", "authors": [], "year": 2022, "venue": "BMJ Open"},
        )
        self.assertIn("study protocol/design", prompt)
        self.assertIn("No outcomes reported", prompt)
        self.assertIn("Never infer results from power calculations", prompt)
        self.assertIn("If metadata title is generic", prompt)

    def test_semaglutide_ckd_is_tagged_diabetes_domains(self):
        tags = auto_tag(
            "Semaglutide for chronic kidney disease in patients with type 2 diabetes",
            "randomized trial reporting cardiovascular outcomes, MACE, cardiovascular outcomes, albuminuria, and eGFR in type 2 diabetes",
        )
        self.assertIn("type-2-diabetes", tags)
        self.assertIn("glp1-ra", tags)
        self.assertIn("ckd", tags)
        self.assertIn("cardiovascular-outcomes", tags)

    def test_normalize_page_body_replaces_generic_heading_and_pico(self):
        body = """# Summary for Diabetes Wiki

## PICO

Population Intervention Comparator Outcome
Patients with type 2 diabetes and chronic kidney disease Semaglutide Placebo Kidney failure or cardiovascular death

## Key Results

No outcome results are reported in this protocol.
"""
        normalized = normalize_page_body(body, "Full Paper Title")
        self.assertTrue(normalized.startswith("# Full Paper Title"))
        self.assertIn("| Component | Description |", normalized)
        self.assertIn("| Intervention | Semaglutide |", normalized)
        self.assertNotIn("Population Intervention Comparator Outcome", normalized)

    def test_protocol_type_is_inferred_from_summary(self):
        self.assertEqual(
            infer_paper_type("ABLATION protocol", "No outcome results are reported in this protocol."),
            "protocol",
        )

    def test_domain_is_inferred_for_ckd_paper(self):
        self.assertEqual(
            infer_domain(
                "Semaglutide for chronic kidney disease in type 2 diabetes",
                "Patients with type 2 diabetes, albuminuria, eGFR decline, and kidney outcomes.",
            ),
            "cardiorenal-metabolic",
        )

    def test_domain_hint_overrides_inference(self):
        self.assertEqual(
            infer_domain("General diabetes paper", "HbA1c and kidney outcomes.", "guidelines-care-models"),
            "guidelines-care-models",
        )


if __name__ == "__main__":
    unittest.main()
