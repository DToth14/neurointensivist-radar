import unittest
from collector.collect import clean_url, is_physician_job, loc_state, normalize, stable_id

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

    def test_normalize_and_stable_id(self):
        record = {"title":"Neurocritical Care Physician","company":"Test Health","location":"New York, NY","url":"https://jobs.example.com/1?utm_source=x","description":"MD/DO"}
        j = normalize(record,"Test")
        self.assertIsNotNone(j)
        self.assertEqual(j["state"],"NY")
        self.assertEqual(j["url"],"https://jobs.example.com/1")
        self.assertEqual(j["id"],stable_id(j))
        self.assertIsNone(normalize({**record,"title":"Neuro ICU Nurse Practitioner"},"Test"))

if __name__ == "__main__": unittest.main()
