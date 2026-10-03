# Hermes Video Clipper

**An agent-led video clipping workflow for Hermes, with a local transcription and rendering runtime.**

Turn permitted podcasts, interviews, talks and other speaker-led videos into **separate vertical Shorts**. Hermes reviews the source context, chooses complete moments, checks captions and shot framing, and drives local Whisper, MediaPipe, FFmpeg and HyperFrames through a checkpointed pipeline.

The default workflow finishes the **five strongest distinct clips**, then offers **ten additional text-only ideas** for you to choose. It does not pad weak sources to meet a quota, and it does not render the extras until you ask.

> **This is an agent-led tool, not a fully unattended clipping bot.** The scripts handle media stages and validation; an active Hermes session supplies editorial and framing judgment. Face detection is not automatic active-speaker recognition.

## What it does

- Local **Whisper small transcription**, CPU/int8, with word timestamps and paginated editorial handoffs.
- Source-hash and artifact-hash checkpoints, resumable stages, atomic manifests and Windows process locks.
- Shot-aware camera-cut detection and face association, with explicitly reviewed follow/split/wide framing.
- Black **Inter captions in a padded white box**, using original speaker audio.
- Optional user-supplied music: audio-only extraction, shuffled rotation, configurable gains, cached waveform/onset entry cues and persisted offsets.
- Separate **1080×1920, 30 fps** MP4 delivery, SRT subtitles, source/QA receipts and music provenance.
- Actual headless-browser/layout checks before delivery rendering and full output decode afterward.
- A mandatory cleanup question after **every finished clip, including chosen extras**. No answer means keep. A read-only storage report highlights sizes and shared-source dependencies.

No compilations, invented voiceover, added B-roll, automatic uploads, paid LLM API integration or bundled music/footage. No views, monetization or rights-clearance promises.

## Requirements

- **Native Windows x64**. macOS, Linux, ARM64, WSL and Docker are not supported by this release.
- **Node.js 22 or later**, npm, and Git for installation from GitHub.
- An installed **Hermes Agent** for the agent-led workflow: https://hermes-agent.nousresearch.com/docs/
- Internet access during installation and enough disk space for Python, ML dependencies, models and browser downloads. Expect a substantial first install; an hour-long video is not a small workload.

You do **not** need to install Python, Whisper or FFmpeg manually. Hermes itself is a prerequisite, not installed or reconfigured by this package.

## Install

From PowerShell, Command Prompt or Git Bash:

```bash
npm install --global git+https://github.com/CauseWhyNot-eh/hermes-video-clipper.git
```

This installs directly from this GitHub repository. It is **not** an npm-registry publication; `npm install hermes-video-clipper` is not the documented installation route.

The npm postinstall step sets up:

1. Checksum-verified, project-local **uv**, then managed **Python 3.11.16** and an isolated virtual environment.
2. Pinned **faster-whisper, MediaPipe, OpenCV, yt-dlp** and their Python dependencies.
3. Pinned ungated **Whisper small weights** and a checksum-verified MediaPipe full-range face model.
4. npm dependencies **FFmpeg/FFprobe, HyperFrames and GSAP**.
5. A usable Chrome/headless browser through HyperFrames' browser manager.

Models are downloaded from their upstreams; they are not committed here. Installation is local and does not require a Whisper API key. It does not modify your system Python, register the managed Python globally, connect accounts or install skills into another Hermes profile.

If setup is interrupted, fix the reported network/dependency error and retry:

```bash
hermes-video-clipper setup
```

If you deliberately disable npm lifecycle scripts, run that setup command yourself before use. `HVC_SKIP_SETUP=1` skips the heavy setup step for package inspection/development only. Native install scripts in dependencies may still be needed for FFmpeg/esbuild.

## Create your clipping workspace

```bash
hermes-video-clipper init ./my-clips
hermes-video-clipper doctor --workspace ./my-clips
```

`init` refuses to overwrite an existing path. It copies the workflow, generic channel config and skill into the workspace, creates empty input/output folders, and links the shared installed runtime/models. Keep the package installed while using these workspaces. Your media and outputs live in the workspace, **not** inside the global npm installation.

Open Hermes in `my-clips` and ask:

> Read AGENTS.md and skills/hermes-video-clipper/SKILL.md. Process my permitted video in inputs/podcasts for the innovation destination. Finish your best five separate Shorts, then show ten more text-only ideas.

Set your channel name and preferences in `config/channel.json`. Put your own permitted music in `inputs/music/`, or ask for explicit no-music composition. There are no sample podcast files, private job records, song IDs or personal channel presets in this repository.

## CLI reference

```bash
hermes-video-clipper --help
hermes-video-clipper pipeline --workspace ./my-clips intake "C:/videos/talk.mp4" --rights user_reported --channel innovation
hermes-video-clipper pipeline --workspace ./my-clips transcribe "JOB_JSON_PATH"
hermes-video-clipper retention --workspace ./my-clips "JOB_JSON_PATH"
```

The real job path is returned by intake; replace the placeholders with that path. `user_reported` records your statement, not independently verified permission. Use `confirmed` only when genuinely established.

The pipeline exposes `intake`, `transcribe`, `plan`, `select`, `analyze`, `compose`, `check`, `render`, `approve` and `status`. The runbook explains reviewed word-ID selection and framing schemas:

- [CUSTOM_CLIPPING.md](CUSTOM_CLIPPING.md): stages and command arguments.
- [WORKFLOW.md](WORKFLOW.md): operating policy.
- [skills/hermes-video-clipper/SKILL.md](skills/hermes-video-clipper/SKILL.md): agent entry point and quality/cleanup rules.

## Storage and safety

After each finished clip, the agent asks whether to delete source video, transcription and temporary work. **Nothing is deleted automatically.** Deleting shared originals can prevent extra clips or revisions; the agent must explain that before scoped approval. Current final videos, subtitles, credits and receipts stay protected.

Use only sources and music you are permitted to reuse. Credit is not permission. Do not bypass DRM, logins or platform restrictions. Source URLs may fail because of site-specific access rules; a working local source does not prove every YouTube URL downloads. Public metadata and external publication require your approval. This release has **no uploader**.

Workspace runtime directories are Windows junctions to the installed package. Do not recursively traverse them during cleanup; protect shared runtime/model files. Updating/uninstalling the package can invalidate those links, so do not do it during an active job.

## Development

```bash
git clone https://github.com/CauseWhyNot-eh/hermes-video-clipper.git
cd hermes-video-clipper
npm install
npm test
```

`npm test` runs Node CLI/installer/workspace tests and the Python pipeline regression suite. Tests use explicitly labeled fixtures, not fictional production outputs. Installation/runtime behavior should also be exercised with a permitted source before claiming editorial quality. Changes to media/browser checks must not silently reduce delivery quality.

## License and dependencies

Project code and workflow: **MIT**. Inter retains its SIL OFL notice. ML packages/models, FFmpeg builds, GSAP and browsers keep their upstream terms; **not every dependency is MIT**. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Hermes Video Clipper is a community project, not an official Nous Research product.
