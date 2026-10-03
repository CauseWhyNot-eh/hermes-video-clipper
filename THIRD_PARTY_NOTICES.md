# Third-party components

The project's own workflow/CLI code is MIT licensed. This does **not** relicense third-party packages, weights, browsers, fonts or user media. Binaries/models are downloaded at installation, not committed to this repository.

| Component | Upstream / terms |
|---|---|
| Inter font (bundled) | SIL Open Font License 1.1; complete notice in assets/fonts/OFL.txt |
| HyperFrames 0.8.114 | Apache-2.0; https://www.npmjs.com/package/hyperframes |
| GSAP 3.14.2 | GSAP standard no-charge license, **not MIT**; https://gsap.com/standard-license/ |
| faster-whisper | MIT; https://github.com/SYSTRAN/faster-whisper |
| Systran faster-whisper-small weights | MIT model card; pinned revision 536b0662742c02347bc0e980a01041f333bce120 at https://huggingface.co/Systran/faster-whisper-small |
| MediaPipe and its face detection asset | Apache-2.0 upstream; https://github.com/google-ai-edge/mediapipe ; downloaded asset https://storage.googleapis.com/mediapipe-assets/face_detection_full_range_sparse.tflite |
| uv | MIT / Apache-2.0; https://github.com/astral-sh/uv |
| Managed CPython | PSF license and bundled component notices; https://www.python.org/psf/license/ ; uv uses python-build-standalone distributions |
| ffmpeg-static npm package | GPL-3.0-or-later; https://github.com/eugeneware/ffmpeg-static ; inspect bundled FFmpeg build license/configuration |
| ffprobe-static npm wrapper | MIT wrapper; https://github.com/joshwnj/ffprobe-static ; underlying FFprobe retains FFmpeg's applicable licensing |
| FFmpeg / FFprobe binaries | Licensing depends on build options; https://ffmpeg.org/legal.html ; source and build information via the supplying upstream projects |
| Chrome for Testing / headless shell | Google's downloaded browser distribution has its own terms/notices; https://developer.chrome.com/docs/chromium/new-headless |

Transitive Python and npm dependencies retain their upstream licenses. package-lock.json and requirements-clipping.lock.txt enumerate pinned package versions. Review upstream notices before redistributing downloaded binaries or embedding this tool in another product.

Users supply their own footage/music. This project supplies no reusable podcast footage, music license, copyright clearance, Content ID guarantee or uploader.
