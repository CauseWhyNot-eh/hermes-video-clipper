"""Conservative waveform/onset cue suggestions, not a claim of musical taste or downbeats."""
import math


def analyze_waveform(samples, sample_rate):
    hop = max(1, round(sample_rate * 0.02))
    step = hop / sample_rate
    energy = [math.sqrt(sum(float(x) ** 2 for x in samples[i:i + hop]) / len(samples[i:i + hop]))
              for i in range(0, len(samples), hop)]
    onset = [0.0] + [max(0.0, b - a) for a, b in zip(energy, energy[1:])]
    peak = max(energy, default=0)
    strongest = max(onset, default=0)
    candidates = []
    if peak > 1e-5 and strongest > peak * 0.015:
        ranked = sorted((i for i in range(1, len(onset) - 1)
                         if onset[i] >= strongest * 0.25 and onset[i] >= onset[i - 1]
                         and onset[i] > onset[i + 1]), key=lambda i: (-onset[i], i))
        picked = []
        for index in ranked:
            if all(abs(index - old) * step >= 8 for old in picked):
                picked.append(index)
                if len(picked) >= 12:
                    break
        # Strong sustained entries first; preserve score and evidence for review.
        candidates = [dict(start_s=round(max(0, i * step - 0.02), 3),
                           onset_strength=round(onset[i] / strongest, 4),
                           reason='Measured positive energy onset; starts just before its attack') for i in picked]
    minimum = max(1, round(0.3 / step))
    maximum = min(len(onset) // 2, round(1.2 / step))
    scores = [(lag, sum(a * b for a, b in zip(onset[lag:], onset[:-lag])))
              for lag in range(minimum, maximum + 1)] if strongest > 1e-5 else []
    lag, score = max(scores, key=lambda pair: pair[1], default=(0, 0))
    total = sum(x * x for x in onset)
    confidence = score / total if total else 0
    return dict(schema=1, duration_s=round(len(samples) / sample_rate, 3),
                method='20ms RMS envelope, positive energy onsets and onset autocorrelation',
                beat_interval_s=round(lag * step, 3) if confidence > 0.12 else None,
                rhythmic_confidence=round(confidence, 4), candidates=candidates,
                envelope_step_s=step, rms_envelope=[round(x, 6) for x in energy],
                limitations='Heuristic entry suggestions, not verified bar/downbeat labels or a listening review')


def waveform_svg(analysis):
    energy = analysis['rms_envelope']
    count = max(1, len(energy))
    peak = max(energy, default=0) or 1
    stride = max(1, count // 1000)
    points = ' '.join(f'{i / count * 1000:.2f},{120 - max(energy[i:i+stride]) / peak * 90:.2f}'
                      for i in range(0, count, stride))
    markers = ''.join(f'<line x1="{c["start_s"] / max(analysis["duration_s"], .001) * 1000:.2f}" '
                      f'x2="{c["start_s"] / max(analysis["duration_s"], .001) * 1000:.2f}" y1="10" y2="130" stroke="#d22"/>'
                      for c in analysis['candidates'])
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 160">'
            '<rect width="1000" height="160" fill="white"/>'
            f'<polyline points="{points}" fill="none" stroke="#111" stroke-width="1"/>{markers}'
            '<text x="10" y="150" font-size="14">RMS waveform envelope; red = candidate music entries, not verified downbeats</text></svg>')
