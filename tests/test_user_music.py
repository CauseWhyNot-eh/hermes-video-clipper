import importlib.util
import os
from pathlib import Path
import random
import tempfile
import json
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path(os.environ.get('CLIPPING_SCRATCH') or
               str(Path(os.environ['HERMES_HOME']) / 'cache/scratch' if os.environ.get('HERMES_HOME')
                   else ROOT / '.workflow/scratch'))
SCRATCH.mkdir(parents=True, exist_ok=True)


def module():
    spec = importlib.util.spec_from_file_location('clipping_pipeline', ROOT / 'scripts/clipping_pipeline.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class UserMusicTests(unittest.TestCase):
    def test_destination_presets_and_music_volume_are_explicit(self):
        m = module()
        self.assertTrue(hasattr(m, 'resolve_channel'), 'Separate destination routing is missing')
        innovation = m.resolve_channel(ROOT, 'innovation')
        self.assertEqual(innovation['id'], 'innovation')
        self.assertEqual(innovation['name'], json.loads((ROOT / 'config/channel.json').read_text())['channels']['innovation']['name'])
        self.assertEqual(m.resolve_channel(ROOT, 'whop')['niche'], 'campaign_clipping')
        with self.assertRaises(ValueError):
            m.resolve_channel(ROOT, '../bad')
        faces = {'width': 1280, 'height': 720, 'duration': 1,
                 'shots': [{'id': 'shot-000', 'start': 0, 'end': 1}], 'samples': []}
        framing = {'reviewed': True, 'reviewer': 'fixture', 'shots': [{'shot_id': 'shot-000', 'mode': 'wide'}]}
        from html.parser import HTMLParser
        class Elements(HTMLParser):
            def __init__(self):
                super().__init__(); self.media = []
            def handle_starttag(self, tag, attrs):
                if tag in ('video', 'audio'):
                    self.media.append((tag, dict(attrs)))
        page = Elements()
        page.feed(m.composition_html(faces, framing, [], 1, music=True))
        music = next((tag, attrs) for tag, attrs in page.media if attrs.get('id') == 'music-bed')
        self.assertEqual(music[0], 'audio')
        self.assertEqual(music[1]['data-volume'], '0.2')
        self.assertEqual(music[1]['data-track-index'], '0')
        self.assertEqual(music[1]['src'], 'assets/music.wav')
        self.assertTrue(all(attrs['src'] == 'assets/source.mp4' for tag, attrs in page.media if tag == 'video'))

    def test_video_music_is_extracted_as_audio_only_and_silent_video_is_skipped(self):
        m = module()
        self.assertTrue(hasattr(m, 'user_music_pool'), 'Mixed audio/video music intake is missing')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            root = Path(temporary)
            folder = root / 'inputs/music'
            folder.mkdir(parents=True)
            video = folder / 'song.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=red:size=160x90:rate=30',
                            '-f', 'lavfi', '-i', 'sine=frequency=500', '-t', '1', '-c:v', 'libx264',
                            '-c:a', 'aac', str(video)], check=True)
            silent = folder / 'silent.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-an', '-c:v', 'copy', str(silent)], check=True)
            original = m.sha256(video)
            pool = m.user_music_pool(root)
            self.assertEqual(len(pool), 1)
            extracted = root / 'music.wav'
            m.extract_music(root, pool[0], 0.8, extracted)
            data = json.loads(m.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', extracted]))
            self.assertEqual([s['codec_type'] for s in data['streams']], ['audio'])
            self.assertEqual(m.sha256(video), original)

    def test_shuffle_uses_all_songs_before_repeat_and_avoids_cycle_boundary_repeat(self):
        m = module()
        self.assertTrue(hasattr(m, 'shuffle_pick'), 'User-music shuffle is missing')
        pool = [{'id': name} for name in ['a', 'b', 'c']]
        state = {}
        rng = random.Random(6)
        results = [m.shuffle_pick(pool, state, rng)['id'] for _ in range(9)]
        for index in range(0, 9, 3):
            self.assertEqual(set(results[index:index + 3]), {'a', 'b', 'c'})
        self.assertTrue(all(a != b for a, b in zip(results, results[1:])))
        self.assertEqual(m.shuffle_pick([{'id': 'solo'}], state, rng)['id'], 'solo')
        with self.assertRaises(ValueError):
            m.shuffle_pick([], state, rng)


if __name__ == '__main__':
    unittest.main()
