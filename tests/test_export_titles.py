import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path(os.environ.get('CLIPPING_SCRATCH') or str(
    Path(os.environ['HERMES_HOME']) / 'cache/scratch' if os.environ.get('HERMES_HOME') else ROOT / '.workflow/scratch'))
SCRATCH.mkdir(parents=True, exist_ok=True)


def pipeline():
    spec = importlib.util.spec_from_file_location('title_pipeline', ROOT / 'scripts/clipping_pipeline.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExportTitleTests(unittest.TestCase):
    def test_export_uses_title_without_job_id_directory(self):
        p = pipeline()
        self.assertTrue(hasattr(p, 'export_path'), 'Readable title export allocation is missing')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            root = Path(temporary)
            job = {'root': str(root), 'id': 'abcdef1234567890', 'verification_only': False, 'channel': {'id': 'innovation'}}
            clip = {'id': 'internal-id', 'name': 'A Complete Thought'}
            output = p.export_path(job, clip)
            self.assertEqual(output, root / 'output/final/innovation/A Complete Thought.mp4')
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b'approved fixture')
            self.assertEqual(p.export_path(job, clip), output)
            self.assertEqual(output.read_bytes(), b'approved fixture')

    def test_duplicate_title_and_orphan_sidecar_are_not_overwritten(self):
        p = pipeline()
        self.assertTrue(hasattr(p, 'export_path'), 'Readable title export allocation is missing')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            root = Path(temporary)
            folder = root / 'output/final/innovation'
            folder.mkdir(parents=True)
            (folder / 'Same Title.mp4').write_bytes(b'approved')
            (folder / 'Same Title (2).srt').write_text('approved subtitles')
            job = {'root': str(root), 'id': 'different-job', 'verification_only': False, 'channel': {'id': 'innovation'}}
            result = p.export_path(job, {'id': 'new', 'name': 'Same Title'})
            self.assertEqual(result.name, 'Same Title (3).mp4')
            self.assertEqual((folder / 'Same Title.mp4').read_bytes(), b'approved')

    def test_windows_safe_names_preserve_unicode_and_block_path_escape(self):
        p = pipeline()
        self.assertTrue(hasattr(p, 'export_path'), 'Readable title export allocation is missing')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            for title, expected in [('Why: now? / Build* better.', 'Why now Build better.mp4'),
                                    ('CON', 'Clip - CON.mp4'), ('../..', 'Untitled clip.mp4'),
                                    ('The Build–Measure–Learn Loop', 'The Build–Measure–Learn Loop.mp4')]:
                job = {'root': temporary, 'id': title, 'verification_only': True, 'channel': {'id': 'fitness'}}
                result = p.export_path(job, {'id': 'fixture', 'name': title})
                self.assertEqual(result.name, expected)
                self.assertEqual(result.parent, Path(temporary) / 'output/verification/fitness')
            with self.assertRaises(ValueError):
                p.export_path({'root': temporary, 'verification_only': False, 'channel': {'id': '../escape'}}, {'id': 'x', 'name': 'Title'})
