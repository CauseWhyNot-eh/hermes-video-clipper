import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path(os.environ.get('CLIPPING_SCRATCH') or
               str(Path(os.environ['HERMES_HOME']) / 'cache/scratch' if os.environ.get('HERMES_HOME')
                   else ROOT / '.workflow/scratch'))
SCRATCH.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('retention_report', ROOT / 'scripts/retention_report.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RetentionReportTests(unittest.TestCase):
    def test_reports_shared_source_without_deleting_anything(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            root = Path(temporary)
            source = root / 'source.mp4'
            source.write_bytes(b'fixture-only')
            for name in ('first', 'extra'):
                job = root / 'library/manifests/clipping' / name / 'job.json'
                job.parent.mkdir(parents=True)
                job.write_text(json.dumps({'root': str(root), 'source': {'path': str(source), 'sha256': 'fixture'}}))
            before = sorted(str(p.relative_to(root)) for p in root.rglob('*'))
            result = module.report(root / 'library/manifests/clipping/first/job.json')
            self.assertEqual(result['source_bytes'], len(b'fixture-only'))
            self.assertEqual(len(result['other_jobs_using_source']), 1)
            self.assertFalse(result['deletion_authorized'])
            self.assertTrue(result['question_required_after_each_finished_clip'])
            self.assertEqual(before, sorted(str(p.relative_to(root)) for p in root.rglob('*')))
            self.assertEqual(source.read_bytes(), b'fixture-only')

    def test_rejects_job_outside_manifest_scope(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            root = Path(temporary)
            job = root / 'job.json'
            job.write_text(json.dumps({'root': str(root), 'source': {'path': str(root / 'source'), 'sha256': 'fixture'}}))
            with self.assertRaises(ValueError):
                module.report(job)
