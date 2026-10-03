---
name: hermes-video-clipper
description: Use when turning permitted videos into separate Shorts.
version: 0.1.0
license: MIT
platforms: [windows]
---

# Hermes Video Clipper

Operate a workspace created with `hermes-video-clipper init`. Read AGENTS.md, WORKFLOW.md, CUSTOM_CLIPPING.md, config/channel.json and current STATUS.md first. If status is missing, create it from observed checks. The scripts implement stages; the Hermes agent supplies editorial, caption and framing judgment. Installing this skill alone does not install the runtime; see README.

## Production

1. Run `hermes-video-clipper doctor --workspace PATH`. Preserve concurrent edits, media and existing checkpoints. Work only on sources the user has supplied or explicitly requested with genuine permitted-reuse status. Credit is not permission; never bypass DRM, logins, bot restrictions or gated model terms.
2. Use `hermes-video-clipper pipeline --workspace PATH intake SOURCE --rights user_reported --channel innovation` (or confirmed when actually established). Record original source links and hashes. Read available full-source transcripts for discovery; use fresh excerpt word timings where appropriate. Never fabricate words, boundaries or checkpoint success.
3. Review full context and rank fifteen distinct complete moments best-first. Use `plan JOB candidates.json` via pipeline to finish only the strongest five automatically. Return ten additional text-only ideas with exactly Name | One-line topic | Duration | Source. Extras require user choice; explain genuine shortfalls, no padding. Scores and IDs stay internal.
4. Run analyze; inspect real contact sheets/video and review each follow/split/wide shot explicitly. Face association is not active-speaker recognition. Preserve charts and gestures; fall back to wide/split when needed.
5. Correct transcription names/numbers and caption boundaries before delivery rendering. New captions are black Inter on a padded white box. Preserve approved existing videos. Original speech only, no extra narration/B-roll/compilation or invented watermark.
6. Compose with user-supplied permitted music, default gain 20%; configure track-specific overrides explicitly. Cache waveform/onset cues, persist the actual selected offset and reuse it on retry. These are heuristic entries, not guaranteed downbeats. Never speed up or retime speech. Explicit --no-music is supported.
7. Actual browser/layout check, 1080x1920/30fps render and full decode are mandatory. Inspect complete exports for editorial meaning, text, cuts and speech/music balance. Contact sheets are not a full listening review. Record limitations; approve only checks actually performed. Deliver separate local files and sidecars, then update STATUS.md.

## Cleanup after every finished clip

Ask whether the user wants the source video, transcription and temporary work deleted after each finished clip, including chosen extras. No answer means keep. This storage question need not pause production of the remaining authorized five.

Use `hermes-video-clipper retention --workspace PATH JOB` to measure sizes and source dependencies. Explain effects on remaining extras/revisions. Get explicit path-level scope approval before deleting anything. Reject links/out-of-workspace targets; ensure no active task needs them. Protect all current final MP4s/subtitles/credits/receipts, music, models, code/config/catalogue. Save a cleanup receipt outside deleted folders, verify targets absent and protected hashes unchanged, then update STATUS. Never silently delete a shared source with one clip's temporary work.

## Boundaries

Native Windows x64 only in this release. No AutoClip, SupoClip, WSL or Docker. No background daemon or automatic uploads. Paid services, account changes and publication require explicit approval. Optimize checkpoint reuse and pre-render corrections, not required quality checks. Follow CUSTOM_CLIPPING.md for exact commands and schemas; use real tool output for every success claim.
