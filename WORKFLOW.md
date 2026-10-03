# Workspace workflow

The Hermes agent, not a separate LLM API, reviews context and chooses useful moments. Installing the runtime does not create an unattended clipping bot.

1. Initialize a new workspace with `hermes-video-clipper init PATH`; set channel names/preferences in `config/channel.json`.
2. Put permitted sources in inputs/podcasts and optional music in inputs/music. URL intake requires explicit permission and normal accessible content; no access bypass.
3. Run doctor, intake and transcribe through the CLI. Reuse validated source/transcript hashes. Read all transcript context; selected-excerpt timings can avoid repeated full-episode transcription when a real full-source transcript already exists.
4. Review/rank fifteen distinct complete moments. Plan selects five for automatic production; ten extras remain text-only until chosen. Never pad a source with weak/duplicate clips.
5. Analyze selected shots. Review every follow/split/wide decision; protect diagrams, gestures and full-body demonstrations. Face detection/association is not active-speaker inference.
6. Correct ASR captions from the actual speech. Black Inter text in a padded white box. Preserve approved existing outputs and make revisions separately.
7. Compose, run real browser check, render separate 1080x1920/30fps files, fully decode and inspect editorial/caption/framing/audio behavior. No quality downgrade or speech speedup. Mark approval only for checks actually performed.
8. Deliver MP4/SRT/receipts/credits locally. Ask after every clip about deleting its source/transcript/work. Read-only retention reporting helps identify sizes/shared dependencies. Keep by default; delete only explicitly approved scope with protected-file hash checks and a receipt.
9. Update STATUS.md. Public metadata and any future external publication require user approval. This release has no uploader, account connection or background supervisor.

See CUSTOM_CLIPPING.md for exact commands and JSON fields. See the skill for durable quality, safety and retention rules.
