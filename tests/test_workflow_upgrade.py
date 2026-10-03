import importlib.util
from pathlib import Path
import unittest
import math
import json
import tempfile
import wave
from array import array

ROOT = Path(__file__).resolve().parents[1]


def pipeline():
    spec = importlib.util.spec_from_file_location('workflow_pipeline', ROOT / 'scripts/clipping_pipeline.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorkflowUpgradeTests(unittest.TestCase):
    def test_ranked_plan_selects_five_and_leaves_ten_as_text_only(self):
        p = pipeline()
        self.assertTrue(hasattr(p, 'partition_candidates'), 'Five-plus-ten planning is missing')
        words = [{'id': f'W{i:06}', 'start': i, 'end': i + 0.8, 'text': 'fixture'} for i in range(60)]
        clips = [{'id': f'clip-{i:02}', 'name': f'Fixture {i}', 'topic': 'Test only',
                  'first_word_id': f'W{i*4:06}', 'last_word_id': f'W{i*4+1:06}', 'context_reviewed': True}
                 for i in range(15)]
        payload = {'reviewer': 'test', 'rank_order_confirmed': True, 'clips': clips}
        result = p.partition_candidates(payload, {'words': words}, 60)
        self.assertEqual([c['id'] for c in result['clips']], [c['id'] for c in clips[:5]])
        self.assertEqual(len(result['extra_ideas']), 10)
        self.assertTrue(all(c['render_authorized'] is False for c in result['extra_ideas']))
        with tempfile.TemporaryDirectory(dir=p.SCRATCH) as temp:
            root = Path(temp)
            source = root / 'fixture.mp4'
            p.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=gray:size=160x90:rate=1',
                   '-f', 'lavfi', '-i', 'anullsrc=r=16000:cl=mono', '-t', '60', '-c:v', 'libx264',
                   '-c:a', 'aac', source])
            jobpath = p.intake(root, str(source), 'confirmed', verification_only=True)
            with p.stage(jobpath, 'transcript') as job:
                artifact = jobpath.parent / 'transcript.json'
                p.save_json(artifact, {'fixture_only': True, 'source_sha256': job['source']['sha256'],
                                       'words': words, 'segments': []})
                p.complete(job, 'transcript', artifact)
            candidates = root / 'candidates.json'
            p.save_json(candidates, payload)
            saved = p.plan(jobpath, candidates)
            actual = p.read_json(jobpath)
            self.assertEqual(len(actual['clips']), 5)
            self.assertEqual(saved['extra_idea_count'], 10)
            self.assertEqual(Path(saved['extra_ideas']).read_text(encoding='utf-8').count('| Fixture'), 10)
            self.assertFalse((jobpath.parent / 'clips').exists())
            self.assertFalse(any(k.startswith('render:') for k in actual['stages']))
        with self.assertRaises(ValueError):
            p.partition_candidates(dict(payload, clips=clips[:4]), {'words': words}, 60)
        fewer = p.partition_candidates(dict(payload, clips=clips[:4], shortfall_reason='Only four clean moments'), {'words': words}, 60)
        self.assertEqual(len(fewer['clips']), 4)
        self.assertEqual(fewer['extra_ideas'], [])
        with self.assertRaises(ValueError):
            p.partition_candidates(dict(payload, clips=clips + [clips[0]]), {'words': words}, 60)

    def test_cached_music_cue_is_used_for_audio_only_extraction(self):
        p = pipeline()
        self.assertTrue(hasattr(p, 'music_cue'), 'Cached cue selection is missing')
        with tempfile.TemporaryDirectory(dir=p.SCRATCH) as temp:
            root = Path(temp)
            source = root / 'song.wav'
            rate = 2000
            samples = array('h', [0 if t < 2 else int(14000 * math.sin(2 * math.pi * 80 * t)
                                                    * math.exp(-((t - 2) % 0.5) * 30))
                                  for t in (i / rate for i in range(rate * 24))])
            with wave.open(str(source), 'wb') as w:
                w.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
                w.writeframes(samples.tobytes())
            track = {'id': 'fixture', 'path': 'song.wav', 'sha256': p.sha256(source), 'duration_seconds': 24}
            cue = p.music_cue(root, track, 0.8)
            self.assertGreater(cue['start_s'], 1.8)
            cache = Path(cue['analysis_path'])
            before = cache.stat().st_mtime_ns
            again = p.music_cue(root, track, 0.8)
            self.assertEqual(cache.stat().st_mtime_ns, before)
            self.assertEqual(again['analysis_sha256'], cue['analysis_sha256'])
            output = root / 'cue.wav'
            p.extract_music(root, track, 0.8, output, start_s=cue['start_s'])
            with wave.open(str(output), 'rb') as audio:
                decoded = array('h', audio.readframes(audio.getnframes()))
                self.assertEqual(audio.getnchannels(), 2)
                self.assertAlmostEqual(audio.getnframes() / audio.getframerate(), 0.8, delta=0.01)
            self.assertGreater(max(abs(x) for x in decoded), 1000)
            self.assertEqual(p.sha256(source), track['sha256'])

    def test_waveform_finds_nonzero_rhythmic_entries_after_quiet_intro(self):
        p = pipeline()
        self.assertTrue(hasattr(p, 'analyze_waveform'), 'Music entry analysis is missing')
        rate = 2000
        samples = [0.0 if t < 2 else (math.sin(2 * math.pi * 80 * t) * math.exp(-((t - 2) % 0.5) * 30))
                   for t in (i / rate for i in range(rate * 24))]
        result = p.analyze_waveform(samples, rate)
        self.assertTrue(result['candidates'])
        self.assertGreater(result['candidates'][0]['start_s'], 1.8)
        self.assertLess(result['candidates'][0]['start_s'], 2.6)
        self.assertAlmostEqual(result['beat_interval_s'], 0.5, delta=0.06)
        self.assertTrue(all(0 <= item['start_s'] < result['duration_s'] for item in result['candidates']))
        quiet = p.analyze_waveform([0.0] * rate, rate)
        self.assertEqual(quiet['candidates'], [])

    def test_new_caption_style_is_black_text_on_white_box(self):
        p = pipeline()
        faces = {'width': 1280, 'height': 720, 'shots': [{'id': 'shot-0', 'start': 0, 'end': 1}], 'samples': []}
        framing = {'reviewed': True, 'reviewer': 'test', 'shots': [{'shot_id': 'shot-0', 'mode': 'wide'}]}
        page = p.composition_html(faces, framing, [{'text': 'Test only', 'start': 0, 'end': 1}], 1)
        self.assertIn('background:#fff', page)
        self.assertIn('color:#000', page)
        self.assertIn('padding:16px 24px', page)
        self.assertNotIn('-webkit-text-stroke:3px black', page)


if __name__ == '__main__':
    unittest.main()
