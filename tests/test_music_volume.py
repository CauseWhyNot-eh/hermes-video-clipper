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


def pipeline():
    spec = importlib.util.spec_from_file_location('volume_pipeline', ROOT / 'scripts/clipping_pipeline.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class MusicVolumeTests(unittest.TestCase):
    def test_track_override_reaches_audio_markup_without_changing_speech(self):
        m = pipeline()
        self.assertTrue(hasattr(m, 'music_volume'), 'Per-track music gain is not supported')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root = Path(temp)
            (root / 'config').mkdir()
            config = {'music_preference': {'volume': 0.2, 'track_volume_overrides': {'te': 0.05}}}
            (root / 'config/channel.json').write_text(json.dumps(config), encoding='utf-8')
            gain = m.music_volume(root, {'id': 'te'})
            self.assertEqual(gain, 0.05)
            self.assertEqual(m.music_volume(root, {'id': 'other'}), 0.2)
            faces = {'width': 1280, 'height': 720, 'duration': 1,
                     'shots': [{'id': 'shot-000', 'start': 0, 'end': 1}], 'samples': []}
            framing = {'reviewed': True, 'reviewer': 'fixture',
                       'shots': [{'shot_id': 'shot-000', 'mode': 'wide'}]}
            page = m.composition_html(faces, framing, [], 1, music=True, music_volume=gain)
            from html.parser import HTMLParser
            class Audio(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.attrs = {}
                def handle_starttag(self, tag, attrs):
                    if tag == 'audio':
                        data = dict(attrs)
                        self.attrs[data['id']] = data
            parser = Audio()
            parser.feed(page)
            self.assertEqual(parser.attrs['music-bed']['data-volume'], '0.05')
            self.assertEqual(parser.attrs['original-speech']['data-volume'], '1')
            config['music_preference']['track_volume_overrides']['te'] = float('nan')
            (root / 'config/channel.json').write_text(json.dumps(config), encoding='utf-8')
            with self.assertRaises(ValueError):
                m.music_volume(root, {'id': 'te'})


if __name__ == '__main__':
    unittest.main()
