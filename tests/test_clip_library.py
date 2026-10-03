import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'scripts' / 'clip_library.py'
SCRATCH = Path(os.environ.get('HERMES_TEST_SCRATCH') or os.environ.get('CLIPPING_SCRATCH') or
               str(Path(os.environ['HERMES_HOME']) / 'cache/scratch' if os.environ.get('HERMES_HOME')
                   else ROOT / '.workflow/scratch'))
SCRATCH.mkdir(parents=True, exist_ok=True)

def load_module():
    if not MODULE_PATH.is_file():
        return None
    spec = importlib.util.spec_from_file_location('clip_library', MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class CatalogTests(unittest.TestCase):
    def test_register_source_and_reopen_without_inventing_clips(self):
        module = load_module()
        self.assertIsNotNone(module, 'The project clip catalogue helper is not implemented')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            root = Path(temporary)
            media = root / 'provided.mp4'
            media.write_bytes(b'unit test fixture, not a media-validity assertion')
            catalog = module.Catalog(root / 'catalog.sqlite3')
            source_id = catalog.add_source(media, 'Provided talk', 'user-provided source', 'Speaker', True)
            self.assertTrue(source_id.startswith('S-'))
            self.assertEqual(catalog.choices(), [])
            reopened = module.Catalog(root / 'catalog.sqlite3')
            self.assertEqual(reopened.sources()[0]['name'], 'Provided talk')
            self.assertEqual(reopened.choices(), [])

    def test_import_keeps_highest_half_and_displays_only_requested_fields(self):
        module = load_module()
        self.assertTrue(hasattr(module.Catalog, 'import_clips'), 'Clip import/ranking is not implemented')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            root = Path(temporary)
            source = root / 'source.mp4'
            source.touch()
            catalog = module.Catalog(root / 'catalog.sqlite3')
            source_id = catalog.add_source(source, 'Source podcast', 'https://example.com/user-source', 'Speaker', True)
            candidates = []
            for index, score in enumerate([30, 95, 70, 80, 20]):
                clip = root / f'clip-{index}.mp4'
                clip.touch()
                candidates.append({'title': f'Fixture clip {index}', 'topic': 'Unit-test topic, not real content',
                                   'score': score, 'start_s': index * 10, 'end_s': index * 10 + 8,
                                   'video_path': str(clip)})
            catalog.import_clips(source_id, candidates, reviewed=True)
            self.assertEqual(catalog.keep_top_half(source_id), 3)
            choices = catalog.choices()
            self.assertEqual([c['name'] for c in choices], ['Fixture clip 1', 'Fixture clip 3', 'Fixture clip 2'])
            self.assertEqual(set(choices[0]), {'name', 'topic', 'duration_seconds', 'source'})
            self.assertEqual(choices[0]['duration_seconds'], 8)
            self.assertIn('Source podcast', choices[0]['source'])
            self.assertEqual(catalog.keep_top_half(source_id), 3)

    def test_selected_clips_stay_hidden_across_chats_and_record_music(self):
        module = load_module()
        self.assertTrue(hasattr(module.Catalog, 'select'), 'Persistent selection/finish tracking is not implemented')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            root = Path(temporary)
            source = root / 'source.mp4'
            source.touch()
            exported = root / 'exported.mp4'
            exported.touch()
            final = root / 'final.mp4'
            final.touch()
            database = root / 'catalog.sqlite3'
            catalog = module.Catalog(database)
            source_id = catalog.add_source(source, 'Fixture source', 'user-provided', '', True)
            catalog.import_clips(source_id, [{'title':'Fixture title', 'topic':'Fixture topic', 'score':90,
                                             'start_s':0,'end_s':8,'video_path':str(exported)}], reviewed=True)
            catalog.keep_top_half(source_id)
            clip_id = catalog.choices(internal=True)[0]['id']
            catalog.select([clip_id])
            reopened = module.Catalog(database)
            self.assertEqual(reopened.choices(), [])
            reopened.mark_finished(clip_id, final, 'fixture-track')
            self.assertEqual(reopened.recent_music(), ['fixture-track'])
            reopened.mark_finished(clip_id, final, 'fixture-track')
            self.assertEqual(reopened.recent_music(), ['fixture-track'])
            self.assertEqual(reopened.status()['clips'], {'finished':1})

    def test_command_line_status_and_invalid_media_guard(self):
        import json
        import subprocess
        import sys
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            root = Path(temporary)
            database = root / 'catalog.sqlite3'
            result = subprocess.run([sys.executable, str(MODULE_PATH), '--db', str(database), 'status'], capture_output=True, text=True)
            self.assertTrue(result.stdout.strip(), 'The command-line interface is not implemented')
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout), {'sources':0,'clips':{},'music_uses':0})
            invalid = root / 'not-really-video.mp4'
            invalid.write_text('This is a deliberately invalid test fixture', encoding='utf-8')
            result = subprocess.run([sys.executable, str(MODULE_PATH), '--db', str(database), 'add-source', str(invalid),
                                     '--name','Fixture','--origin','test source','--rights-confirmed'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('error', json.loads(result.stdout))

    def test_later_rights_confirmation_preserves_source_and_enables_import(self):
        module = load_module()
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            root = Path(temporary)
            media = root / 'source.mp4'
            media.touch()
            catalog = module.Catalog(root / 'catalog.sqlite3')
            source_id = catalog.add_source(media, 'Source', 'provided', '', False)
            confirmed_id = catalog.add_source(media, 'Source', 'provided', '', True)
            self.assertEqual(source_id, confirmed_id)
            self.assertEqual(catalog.sources()[0]['rights_confirmed'], 1)

    def test_mutations_have_an_explicit_transaction_before_reading_state(self):
        module = load_module()
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            catalog = module.Catalog(Path(temporary) / 'catalog.sqlite3')
            with catalog.connect() as connection:
                self.assertTrue(connection.in_transaction, 'Acquire transaction before source/clip state reads')

    def test_empty_source_cannot_be_marked_as_ranked(self):
        module = load_module()
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            root = Path(temporary)
            source = root / 'source.mp4'
            source.touch()
            catalog = module.Catalog(root / 'catalog.sqlite3')
            source_id = catalog.add_source(source, 'Source', 'provided', '', True)
            with self.assertRaises(ValueError):
                catalog.keep_top_half(source_id)
            self.assertEqual(catalog.sources()[0]['ranked'], 0)

    def test_invalid_batch_rolls_back_and_requires_confirmed_rights(self):
        module = load_module()
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            root = Path(temporary)
            source, clip = root / 'source.mp4', root / 'clip.mp4'
            source.touch()
            clip.touch()
            catalog = module.Catalog(root / 'catalog.sqlite3')
            source_id = catalog.add_source(source, 'Source', 'provided', '', False)
            item = {'title':'Fixture','topic':'Fixture topic','score':5,'start_s':0,'end_s':1,'video_path':str(clip)}
            with self.assertRaises(ValueError):
                catalog.import_clips(source_id,[item],reviewed=True)
            catalog.add_source(source, 'Source', 'provided', '', True)
            bad = dict(item, start_s=2, end_s=1)
            with self.assertRaises(ValueError):
                catalog.import_clips(source_id,[item,bad],reviewed=True)
            self.assertEqual(catalog.status()['clips'], {})

if __name__ == '__main__':
    unittest.main()
