"""Reviewed crop plans and deterministic HyperFrames HTML."""
import html


def validate_framing(faces, framing):
    if framing.get('reviewed') is not True or not str(framing.get('reviewer', '')).strip():
        raise ValueError('Inspect shots and explicitly review framing first')
    decisions = framing.get('shots', [])
    mapping = {d['shot_id']: d for d in decisions}
    if len(mapping) != len(decisions) or set(mapping) != {s['id'] for s in faces['shots']}:
        raise ValueError('Exactly one decision per detected shot required')
    for shot in faces['shots']:
        decision = mapping[shot['id']]
        mode = decision.get('mode')
        if mode not in ('follow', 'split', 'wide'):
            raise ValueError('Use follow, split or wide framing')
        if mode == 'wide':
            continue
        ids = [decision.get('track_id')] if mode == 'follow' else decision.get('track_ids', [])
        if not all(ids) or (mode == 'split' and len(set(ids)) != 2):
            raise ValueError('Select one follow track or two distinct split tracks')
        samples = [s for s in faces['samples'] if s['shot_id'] == shot['id']]
        for identifier in ids:
            present = [s['t'] for s in samples if any(f['id'] == identifier for f in s['faces'])]
            gaps = [b - a for a, b in zip([shot['start']] + present, present + [shot['end']])]
            if not present or len(present) < 0.8 * len(samples) or max(gaps) > 0.8:
                raise ValueError('Missing/unstable face track; review or choose wide fallback')
    return mapping


def caption_chunks(words, duration):
    chunks, current = [], []
    for word in words:
        if current and (len(current) >= 6 or len(' '.join(w['text'] for w in current + [word])) > 42
                        or word['start'] - current[-1]['end'] > 0.5):
            chunks.append(current)
            current = []
        current.append(word)
    if current:
        chunks.append(current)
    return [{'start': max(0, c[0]['start']), 'end': min(duration, c[-1]['end']),
             'text': ' '.join(w['text'] for w in c)} for c in chunks]


def crop_path(faces, shot, track_id, viewport_h):
    scale = max(1080 / faces['width'], viewport_h / faces['height'])
    width, height = faces['width'] * scale, faces['height'] * scale
    points, smooth_x = [], None
    for sample in faces['samples']:
        if sample['shot_id'] != shot['id']:
            continue
        track = next((f for f in sample['faces'] if f['id'] == track_id), None)
        if not track:
            continue
        x, y, w, h = track['bbox']
        desired = max(1080 - width, min(0, 540 - (x + w / 2) * width))
        smooth_x = desired if smooth_x is None else 0.35 * desired + 0.65 * smooth_x
        offset_y = max(viewport_h - height, min(0, viewport_h * 0.28 - (y + h / 2) * height))
        points.append({'t': sample['t'], 'x': round(smooth_x, 3), 'y': round(offset_y, 3)})
    return width, height, points


def composition_html(faces, framing, words, duration, music=False, music_volume=0.2):
    decisions = validate_framing(faces, framing)
    elements, animation = [], []
    for index, shot in enumerate(faces['shots']):
        decision = decisions[shot['id']]
        begin, end = shot['start'], min(duration, shot['end'])
        if end <= begin:
            continue
        mode = decision['mode']
        ids = decision['track_ids'] if mode == 'split' else [decision.get('track_id')]
        for pane, identifier in enumerate(ids):
            pane_h = 960 if mode == 'split' else 1920
            target = f'motion-{index}-{pane}'
            if mode == 'wide':
                scale = min(1080 / faces['width'], 1920 / faces['height'])
                width, height = faces['width'] * scale, faces['height'] * scale
                points = [{'t': begin, 'x': (1080 - width) / 2, 'y': (1920 - height) / 2}]
            else:
                width, height, points = crop_path(faces, shot, identifier, pane_h)
            elements.append(f'<div class="viewport" style="top:{pane * pane_h}px;height:{pane_h}px">'
                            f'<div id="{target}" class="motion" style="width:{width:.3f}px;height:{height:.3f}px">'
                            f'<video id="video-{index}-{pane}" class="clip" data-track-index="1" src="assets/source.mp4" '
                            f'data-start="{begin:.3f}" data-duration="{end - begin:.3f}" '
                            f'data-media-start="{begin:.3f}" data-volume="0" muted playsinline '
                            'style="width:100%;height:100%"></video></div></div>')
            animation.append(f'tl.set("#{target}",{{x:{points[0]["x"]},y:{points[0]["y"]}}},{begin});')
            for prior, point in zip(points, points[1:]):
                animation.append(f'tl.to("#{target}",{{x:{point["x"]},y:{point["y"]},'
                                 f'duration:{max(0.000001, point["t"] - prior["t"] - 0.000001):.6f},ease:"none"}},{prior["t"]:.3f});')
    for index, caption in enumerate(caption_chunks(words, duration)):
        if caption['end'] > caption['start']:
            elements.append(f'<div id="caption-{index}" class="clip caption" data-track-index="2" data-start="{caption["start"]:.3f}" '
                            f'data-duration="{caption["end"] - caption["start"]:.3f}"><p>{html.escape(caption["text"])}</p></div>')
    elements.append(f'<audio id="original-speech" data-track-index="3" src="assets/audio.wav" data-start="0" data-duration="{duration:.3f}" '
                    'data-volume="1"></audio>')
    if music:
        elements.insert(0, f'<audio id="music-bed" data-track-index="0" src="assets/music.wav" data-start="0" '
                        f'data-duration="{duration:.3f}" data-volume="{music_volume:g}"></audio>')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=1080,height=1920">
<title>Reviewed clip composition</title><script src="assets/gsap.min.js"></script><style>
@font-face{{font-family:Inter;src:url('assets/Inter.ttf')}}
html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#000;color:#fff;font-family:Inter,sans-serif}}
#root{{position:relative;width:1080px;height:1920px;overflow:hidden;background:#000}}
.viewport{{position:absolute;left:0;width:1080px;overflow:hidden;pointer-events:none}}
.motion{{position:absolute;left:0;top:0}}
.caption{{position:absolute;left:80px;bottom:320px;width:920px;display:flex;justify-content:center;align-items:center}}
.caption p{{margin:0;text-align:center;font-size:54px;font-weight:600;line-height:1.2;color:#000;
background:#fff;padding:16px 24px;border-radius:8px;box-sizing:border-box;max-width:100%;overflow-wrap:anywhere}}
</style></head><body><div id="root" data-composition-id="main" data-start="0" data-width="1080"
data-height="1920" data-duration="{duration:.3f}">{''.join(elements)}</div>
<script>window.__timelines=window.__timelines||{{}};const tl=gsap.timeline({{paused:true}});
{''.join(animation)}
tl.to({{}},{{duration:{duration:.3f}}},0);window.__timelines["main"]=tl;</script></body></html>'''


def srt(words, duration):
    def clock(seconds):
        ms = round(seconds * 1000)
        return f'{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}'
    return '\n\n'.join(f'{i + 1}\n{clock(c["start"])} --> {clock(c["end"])}\n{c["text"]}'
                       for i, c in enumerate(caption_chunks(words, duration))) + '\n'
