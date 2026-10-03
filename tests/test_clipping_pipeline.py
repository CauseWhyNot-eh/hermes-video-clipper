import importlib.util
import json
import os
from pathlib import Path
import tempfile
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path(os.environ.get('CLIPPING_SCRATCH') or
               str(Path(os.environ['HERMES_HOME']) / 'cache/scratch' if os.environ.get('HERMES_HOME')
                   else ROOT / '.workflow/scratch'))
SCRATCH.mkdir(parents=True, exist_ok=True)


def load():
    path = ROOT / 'scripts/clipping_pipeline.py'
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location('clipping_pipeline', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PipelineTests(unittest.TestCase):
    def test_exclusive_lock_and_asset_tampering_gate(self):
        module = load()
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            directory = Path(temporary)
            with module.file_lock(directory / 'source.lock'):
                with self.assertRaises(RuntimeError):
                    with module.file_lock(directory / 'source.lock'):
                        self.fail('A concurrent source lock was allowed')
            with module.file_lock(directory / 'source.lock'):
                pass
            asset = directory / 'assets' / 'speech.wav'
            asset.parent.mkdir()
            asset.write_bytes(b'fixture-not-real-audio')
            job = {'stages': {'composition:test': {'asset_hashes': {'speech.wav': module.sha256(asset)}}}}
            module.check_assets(job, 'test', directory)
            asset.write_bytes(b'changed fixture')
            with self.assertRaises(ValueError):
                module.check_assets(job, 'test', directory)

    def test_framing_requires_review_known_tracks_and_escapes_caption_text(self):
        module = load()
        self.assertTrue(hasattr(module, 'composition_html'), 'Reviewed HyperFrames assembly is missing')
        faces = {'width': 1280, 'height': 720, 'duration': 1,
                 'shots': [{'id': 'shot-000', 'start': 0, 'end': 1}],
                 'samples': [{'t': t, 'shot_id': 'shot-000',
                              'faces': [{'id': 'shot-000-face-000', 'bbox': [0.4, 0.2, 0.1, 0.2]}]}
                             for t in [0, 0.2, 0.4, 0.6, 0.8]]}
        framing = {'reviewed': True, 'reviewer': 'fixture',
                   'shots': [{'shot_id': 'shot-000', 'mode': 'follow', 'track_id': 'shot-000-face-000'}]}
        words = [{'start': 0, 'end': 0.8, 'text': '<script>unsafe</script>'}]
        document = module.composition_html(faces, framing, words, 1)
        self.assertIn('&lt;script&gt;unsafe&lt;/script&gt;', document)
        self.assertIn('data-width="1080"', document)
        self.assertIn('window.__timelines["main"]', document)
        with self.assertRaises(ValueError):
            module.composition_html(faces, dict(framing, reviewed=False), words, 1)
        invalid = dict(framing, shots=[{'shot_id': 'shot-000', 'mode': 'follow', 'track_id': 'not-a-track'}])
        with self.assertRaises(ValueError):
            module.composition_html(faces, invalid, words, 1)

    def test_tracks_do_not_follow_detection_order_and_reset_on_camera_cut(self):
        module = load()
        self.assertTrue(hasattr(module, 'associate_faces'), 'Shot-aware tracking is missing')
        left, right = [0.1, 0.2, 0.1, 0.2], [0.7, 0.2, 0.1, 0.2]
        first = module.associate_faces([left, right], [], 'shot-0')
        second = module.associate_faces([right, left], first, 'shot-0')
        self.assertEqual(second[0]['id'], first[1]['id'])
        self.assertEqual(second[1]['id'], first[0]['id'])
        cut = module.associate_faces([left], [], 'shot-1')
        self.assertNotEqual(cut[0]['id'], first[0]['id'])

    def test_intake_preserves_source_requires_rights_and_resumes_transcript(self):
        module = load()
        self.assertTrue(hasattr(module, 'intake'), 'Intake and checkpoint stages are missing')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            root = Path(temporary)
            source = root / 'source.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=30',
                            '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '1', '-c:v', 'libx264',
                            '-c:a', 'aac', str(source)], check=True)
            original = module.sha256(source)
            with self.assertRaises(ValueError):
                module.intake(root, str(source), rights='unconfirmed')
            job_path = module.intake(root, str(source), rights='user_reported', niche='fitness',
                                     campaign={'instructions': 'Fixture campaign, not payout approval'})
            job = module.read_json(job_path)
            self.assertEqual(job['niche'], 'fitness')
            self.assertEqual(job['source']['sha256'], original)
            self.assertEqual(module.sha256(source), original)
            self.assertFalse(job['publishing'])
            self.assertEqual(job['campaign']['payout_status'], 'not_verified')
            cached = job_path.parent / 'transcript.json'
            module.save_json(cached, {'words': [], 'test_fixture': True})
            job['stages']['transcript'] = {'status': 'complete', 'artifact': str(cached), 'sha256': module.sha256(cached)}
            module.save_json(job_path, job)
            self.assertEqual(module.transcribe(job_path), cached)
            source.write_bytes(b'changed fixture')
            with self.assertRaises(ValueError):
                module.transcribe(job_path)

    def test_selection_uses_real_word_ids_and_rejects_unreviewed_or_unsafe_ranges(self):
        module = load()
        self.assertTrue(hasattr(module, 'validate_selection'), 'Selection validator is missing')
        words = [{'id': f'W{i:06}', 'start': i, 'end': i + 0.5, 'text': 'word'} for i in range(4)]
        transcript = {'words': words}
        clip = {'id': 'clip-01', 'name': 'Fixture', 'topic': 'Test only',
                'first_word_id': 'W000000', 'last_word_id': 'W000003', 'context_reviewed': True}
        result = module.validate_selection({'reviewer': 'test', 'clips': [clip]}, transcript, 5)
        self.assertEqual(result[0]['start_s'], 0)
        self.assertEqual(result[0]['end_s'], 3.5)
        for replacement in ({'id': '../escape'}, {'last_word_id': 'W999999'},
                            {'context_reviewed': False}, {'last_word_id': 'W000000', 'first_word_id': 'W000003'}):
            with self.assertRaises(ValueError):
                module.validate_selection({'reviewer': 'test', 'clips': [dict(clip, **replacement)]}, transcript, 5)
        with self.assertRaises(ValueError):
            module.validate_selection({'reviewer': 'test', 'clips': [clip, dict(clip, id='clip-02')]}, transcript, 5)

    def test_manifest_is_atomic_and_source_is_preserved(self):
        module = load()
        self.assertIsNotNone(module, 'The custom pipeline has not been implemented')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            folder = Path(temporary)
            path = folder / 'job.json'
            module.save_json(path, {'niche': 'fitness', 'publishing': False})
            self.assertEqual(module.read_json(path), {'niche': 'fitness', 'publishing': False})
            module.save_json(path, {'niche': 'fitness', 'publishing': False, 'stage': 'intake'})
            self.assertEqual(module.read_json(path)['stage'], 'intake')
            self.assertEqual(list(folder.glob('*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
