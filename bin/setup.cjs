const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const UV_URL = 'https://github.com/astral-sh/uv/releases/download/0.12.17/uv-x86_64-pc-windows-msvc.zip';
const UV_SHA = 'a252121d5b59398fcb137c6ea448176459a44010f33f67e0072305a637119ca7';
const FACE_URL = 'https://storage.googleapis.com/mediapipe-assets/face_detection_full_range_sparse.tflite';
const FACE_SHA = '2c3728e6da56f21e21a320433396fb06d40d9088f2247c05e5635a688d45dfe1';

async function downloadVerified(url, target, expectedSha) {
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const temporary = `${target}.${process.pid}.download`;
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(300000) });
    if (!response.ok) throw new Error(`Download failed: HTTP ${response.status} from ${new URL(url).hostname}`);
    const bytes = Buffer.from(await response.arrayBuffer());
    const digest = crypto.createHash('sha256').update(bytes).digest('hex');
    if (digest !== expectedSha) throw new Error(`SHA-256 mismatch for ${path.basename(target)}; refusing downloaded content`);
    fs.writeFileSync(temporary, bytes);
    fs.renameSync(temporary, target);
  } finally {
    fs.rmSync(temporary, { force: true });
  }
}

function runtimeEnvironment(root) {
  const scratch = process.env.CLIPPING_SCRATCH || (process.env.HERMES_HOME ? path.join(process.env.HERMES_HOME, 'cache', 'scratch') : path.join(root, '.workflow', 'scratch'));
  fs.mkdirSync(scratch, { recursive: true });
  const ffmpeg = require('ffmpeg-static');
  const ffprobe = require('ffprobe-static').path;
  return { ...process.env,
    PATH: [path.dirname(ffmpeg), path.dirname(ffprobe), path.dirname(process.execPath), process.env.PATH || ''].join(path.delimiter),
    CLIPPING_SCRATCH: scratch, TMPDIR: scratch, TEMP: scratch, TMP: scratch,
    UV_PYTHON_INSTALL_DIR: path.join(root, '.runtime', 'python'),
    HYPERFRAMES_SKIP_SKILLS: '1', HF_HUB_DISABLE_TELEMETRY: '1', DO_NOT_TRACK: '1'
  };
}

function execute(command, args, { root, env, capture = false } = {}) {
  const result = spawnSync(command, args, { cwd: root, env, stdio: capture ? 'pipe' : 'inherit', encoding: 'utf8', windowsHide: true });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${path.basename(command)} failed (exit ${result.status}). ${capture ? result.stderr : 'See the output above; fix the cause and run setup again.'}`);
  return capture ? result.stdout : '';
}

async function setup(root) {
  if (process.platform !== 'win32' || process.arch !== 'x64') throw new Error('Hermes Video Clipper v0.1 supports native Windows x64 only.');
  if (process.env.HVC_SKIP_SETUP === '1') {
    console.log('Runtime setup skipped by HVC_SKIP_SETUP=1. Run hermes-video-clipper setup before use.');
    return;
  }
  const env = runtimeEnvironment(root);
  const runtime = path.join(root, '.runtime');
  const uvDir = path.join(runtime, 'uv');
  const uv = path.join(uvDir, 'uv.exe');
  fs.mkdirSync(runtime, { recursive: true });
  if (!fs.existsSync(uv)) {
    console.log('Installing checksum-verified uv 0.12.17 (project-local; no system PATH changes).');
    const zip = path.join(runtime, 'uv.zip');
    await downloadVerified(UV_URL, zip, UV_SHA);
    const quote = value => `'${value.replace(/'/g, "''")}'`;
    execute('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', `Expand-Archive -LiteralPath ${quote(zip)} -DestinationPath ${quote(uvDir)} -Force`], { root, env });
    fs.rmSync(zip, { force: true });
    if (!fs.existsSync(uv)) throw new Error('uv archive layout changed; setup stopped safely.');
  }
  console.log('Installing managed Python 3.11 and isolated transcription/framing dependencies.');
  execute(uv, ['python', 'install', '3.11.16', '--no-bin', '--no-registry'], { root, env });
  const python = path.join(root, '.clipping-venv', 'Scripts', 'python.exe');
  if (!fs.existsSync(python)) execute(uv, ['venv', '--managed-python', '--python', '3.11.16', path.join(root, '.clipping-venv')], { root, env });
  execute(uv, ['pip', 'sync', '--python', python, path.join(root, 'requirements-clipping.lock.txt')], { root, env });
  console.log('Downloading pinned local Whisper small weights (MIT) and verified MediaPipe face model (Apache-2.0).');
  execute(python, [path.join(root, 'scripts', 'install_models.py'), root], { root, env });
  const face = path.join(root, 'assets', 'models', 'blaze_face_full_range_sparse.tflite');
  if (!fs.existsSync(face) || crypto.createHash('sha256').update(fs.readFileSync(face)).digest('hex') !== FACE_SHA) {
    await downloadVerified(FACE_URL, face, FACE_SHA);
  }
  const rendererModules = path.join(root, 'tools', 'hyperframes', 'node_modules');
  fs.mkdirSync(path.dirname(rendererModules), { recursive: true });
  if (!fs.existsSync(rendererModules)) fs.symlinkSync(path.join(root, 'node_modules'), rendererModules, 'junction');
  console.log('Ensuring Chrome for actual browser checks and delivery rendering.');
  execute(process.execPath, [path.join(root, 'node_modules', 'hyperframes', 'dist', 'cli.js'), 'browser', 'ensure'], { root, env });
  execute(python, ['-c', 'import faster_whisper, mediapipe, cv2; print("Transcription/framing imports verified")'], { root, env });
  execute(require('ffmpeg-static'), ['-version'], { root, env, capture: true });
  execute(require('ffprobe-static').path, ['-version'], { root, env, capture: true });
  fs.writeFileSync(path.join(runtime, 'setup.json'), JSON.stringify({ complete: true, version: '0.1.0', platform: 'windows-x64', whisperRevision: '536b0662742c02347bc0e980a01041f333bce120', faceSha256: FACE_SHA }, null, 2));
  console.log('Hermes Video Clipper runtime installed. Next: hermes-video-clipper init ./my-clips');
}

module.exports = { downloadVerified, runtimeEnvironment, execute, setup };
