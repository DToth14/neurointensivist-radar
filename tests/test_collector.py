import unittest
from collector.collect import clean_url, is_physician_job, loc_state, normalize, stable_id, visa_classification, combine_job

class JobFilterTests(unittest.TestCase):
    def test_neurointensivist(self):
        self.assertTrue(is_physician_job("Academic Neurointensivist", "MD/DO required")[0])

    def test_nonphysician_is_excluded(self):
        for title in ("Neurocritical Care Nurse Practitioner", "Neuro ICU Registered Nurse", "Neuro Critical Care Physician Assistant", "Neurocritical Care Fellowship", "Neurocritical Care Pharmacist"):
            self.assertFalse(is_physician_job(title, "physician led neuro ICU service")[0],title)

    def test_generic_neurologist_not_automatically_accepted(self):
        self.assertFalse(is_physician_job("Outpatient Neurologist", "clinic patients")[0])

    def test_description_supports_ambiguous_neurocritical_title(self):
        self.assertTrue(is_physician_job("Neuro Intensive Care Unit Faculty", "Candidates must hold MD/DO board certification")[0])

    def test_location_states(self):
        self.assertEqual(loc_state("Murray, Utah"),"UT")
        self.assertEqual(loc_state("Gainesville, GA"),"GA")
        self.assertEqual(loc_state("Remote (US)"),"REMOTE")

    def test_explicit_h1b_sponsorship(self):
        for phrase in (
            "We offer H-1B visa sponsorship for qualified physicians.",
            "H1B sponsorship available for board certified physicians.",
            "Visa sponsorship available for H-1B physicians.",
        ):
            self.assertEqual(visa_classification(phrase)[0], "h1b_offered", phrase)

    def test_other_sponsorship_is_not_h1b_confirmation(self):
        self.assertEqual(visa_classification("Visa sponsorship is available." )[0], "visa_offered")
        self.assertEqual(visa_classification("We support immigration sponsorship for physicians." )[0], "visa_offered")

    def test_h1b_mentioned_does_not_imply_sponsorship(self):
        self.assertEqual(visa_classification("H-1B applicants may apply.")[0], "needs_review")
        self.assertEqual(visa_classification("Neuro ICU attendings wanted.")[0], "not_stated")
        self.assertEqual(visa_classification("Applicants must possess a current valid work visa.")[0], "not_stated")

    def test_exclusion_of_sponsorship(self):
        for phrase in (
            "We cannot sponsor H1B visas at this time.",
            "Visa sponsorship is not available for this position.",
            "Must be authorized to work without sponsorship.",
            "No H-1B sponsorship will be offered.",
        ):
            self.assertEqual(visa_classification(phrase)[0], "no_sponsorship", phrase)

    def test_h1b_terms_outrank_other_visa_terms(self):
        self.assertEqual(visa_classification("We do not sponsor J-1 visas. H-1B sponsorship is available.")[0], "h1b_offered")
        self.assertEqual(visa_classification("J-1 visa sponsorship available but no H-1B sponsorship.")[0], "no_sponsorship")

    def test_full_description_is_checked_even_when_ui_excerpt_is_short(self):
        full = "A" * 700 + " H-1B sponsorship available for eligible applicants."
        record = {"title":"Neurocritical Care Physician","company":"Test Health","location":"Baltimore, MD","url":"https://jobs.example.com/7","description":full}
        j = normalize(record,"Test")
        self.assertEqual(j["visa_status"], "h1b_offered")
        self.assertIn("H-1B", j["visa_evidence"])
        self.assertNotIn("H-1B", j["description"])

    def test_keep_prior_visa_evidence_when_feed_snippet_truncated(self):
        previous = {"visa_status":"h1b_offered","visa_evidence":"H-1B sponsorship available", "sources":["A"], "description":"Job", "first_seen":"2026-01-01"}
        newest = {"visa_status":"not_stated","visa_evidence":"", "sources":["A"], "description":"Job", "status":"active"}
        merged = combine_job(previous, newest, "2026-10-24T00:00:00Z")
        self.assertEqual(merged["visa_status"], "h1b_offered")

    def test_normalize_and_stable_id(self):
        record = {"title":"Neurocritical Care Physician","company":"Test Health","location":"New York, NY","url":"https://jobs.example.com/1?utm_source=x","description":"MD/DO"}
        j = normalize(record,"Test")
        self.assertIsNotNone(j)
        self.assertEqual(j["state"],"NY")
        self.assertEqual(j["url"],"https://jobs.example.com/1")
        self.assertEqual(j["id"],stable_id(j))
        self.assertIsNone(normalize({**record,"title":"Neuro ICU Nurse Practitioner"},"Test"))

if __name__ == "__main__": unittest.main()
