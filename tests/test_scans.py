import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from collector import collect


class ScannerReliabilityTests(unittest.TestCase):
    def test_no_results_success_does_not_crash_or_stop_other_queries(self):
        cfg={"serpapi_queries":["neurointensivist physician"],"serpapi_regions":["Boston, MA","New York, NY"]}
        def api(_url, params=None, **kwargs):
            if params["location"]=="Boston, MA":
                return {"search_metadata":{"status":"Success"},"error":"Google hasn't returned any results for this query."}
            return {"search_metadata":{"status":"Success"},"jobs_results":[{
                "title":"Neurocritical Care Physician", "company_name":"Example Health",
                "location":"New York, NY", "description":"MD/DO physician", "apply_options":[{"link":"https://example.org/apply"}]
            }]}
        with patch.object(collect,'get_json',side_effect=api), patch.dict(os.environ,{'MAX_SERPAPI_QUERIES_PER_RUN':'2'}):
            jobs=collect.from_serpapi('redacted',cfg)
        self.assertEqual(len(jobs),1)
        self.assertEqual(collect.QUERY_DIAGNOSTICS['empty_queries'],1)
        self.assertEqual(collect.QUERY_DIAGNOSTICS['failed_queries'],0)

    def test_unauthorized_query_marks_failure(self):
        cfg={"serpapi_queries":["neurointensivist physician"],"serpapi_regions":["Boston, MA"]}
        with patch.object(collect,'get_json',return_value={"search_metadata":{"status":"Error"},"error":"Invalid API key"}):
            with self.assertRaises(RuntimeError):
                collect.from_serpapi('redacted',cfg)

    def test_empty_success_scan_is_not_a_source_error(self):
        cfg={"serpapi_queries":["neurointensivist physician"],"serpapi_regions":["Boston, MA"]}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'sources.json').write_text(json.dumps(cfg))
            (p/'jobs.json').write_text(json.dumps({'meta':{},'jobs':[]}))
            with patch.object(collect,'DATA_DIR',p),patch.dict(os.environ,{'SERPAPI_KEY':'redacted','MAX_SERPAPI_QUERIES_PER_RUN':'1'},clear=True),patch.object(collect,'get_json',return_value={'search_metadata':{'status':'Success'},'error':"Google hasn't returned any results for this query."}):
                result=collect.run()
            self.assertEqual(result['meta']['scan_state'],'complete')
            self.assertEqual(result['meta']['monitored_sources'],1)
            self.assertEqual(result['meta']['active_count'],0)
            self.assertIsNotNone(result['meta']['last_scan_at'])
            self.assertEqual(result['jobs'],[])

    def test_unconfigured_scan_is_reported_without_fake_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'sources.json').write_text(json.dumps({'greenhouse':[],'lever':[],'ashby':[],'smartrecruiters':[],'workday':[]}))
            (p/'jobs.json').write_text(json.dumps({'meta':{},'jobs':[]}))
            with patch.object(collect,'DATA_DIR',p),patch.dict(os.environ,{},clear=True):
                result=collect.run()
            self.assertEqual(result['meta']['scan_state'],'unconfigured')
            self.assertIsNotNone(result['meta']['last_scan_at'])
            self.assertEqual(result['jobs'],[])

    def test_h1b_filter_is_opt_in_in_ui(self):
        index=(Path(__file__).resolve().parents[1]/'index.html').read_text()
        js=(Path(__file__).resolve().parents[1]/'app.js').read_text()
        self.assertIn('id="advancedFilters" hidden',index)
        self.assertIn('<option value="all">Any sponsorship status</option>',index)
        self.assertIn("visa:params.get('visa')||'all'",js)
        self.assertIn("if(ui.visa!=='all')",js)

    def test_workflow_has_no_git_push_or_write_permission(self):
        workflow=(Path(__file__).resolve().parents[1]/'.github/workflows/radar.yml').read_text()
        self.assertIn("cron: '7 * * * *'",workflow)
        self.assertIn('contents: read',workflow)
        self.assertNotIn('git push ',workflow)
        self.assertNotIn('contents: write',workflow)
        self.assertIn('actions/cache/restore@v4',workflow)
        self.assertIn('actions/cache/save@v4',workflow)

if __name__=='__main__':unittest.main()
