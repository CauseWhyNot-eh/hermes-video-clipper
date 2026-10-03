#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');
const { initWorkspace } = require('./runtime.cjs');
const { setup, runtimeEnvironment, execute } = require('./setup.cjs');
const root = path.resolve(__dirname, '..');

const help = `Hermes Video Clipper v0.1.0 — native Windows x64, agent-led Shorts\n\nCommands:\n  setup                            Install/retry the local runtime and models\n  init PATH                        Create a new workspace (never overwrites)\n  doctor [--workspace PATH]        Check installed runtime and workspace\n  pipeline [--workspace PATH] ...  Run intake/transcribe/plan/analyze/compose/check/render\n  retention [--workspace PATH] JOB Read-only cleanup size/dependency report\n  test-python                      Run the Python regression suite\n\nAn active Hermes agent reviews and chooses moments; this is not an unattended bot.\nSee README.md and CUSTOM_CLIPPING.md. No automatic uploads or source deletion.\n`;

async function main() {
  const args = process.argv.slice(2);
  const command = args.shift() || '--help';
  if (['--help', '-h', 'help'].includes(command)) { console.log(help); return; }
  if (command === '--version') { console.log('0.1.0'); return; }
  if (!['setup', 'init', 'doctor', 'pipeline', 'retention', 'test-python'].includes(command)) throw new Error(`Unknown command: ${command}. Use --help.`);
  if (command === 'setup') { await setup(root); return; }
  if (process.platform !== 'win32' || process.arch !== 'x64') throw new Error('This release supports native Windows x64 only.');
  const python = path.join(root, '.clipping-venv', 'Scripts', 'python.exe');
  if (!fs.existsSync(python) || !fs.existsSync(path.join(root, '.runtime', 'setup.json'))) throw new Error('Runtime setup incomplete. Run hermes-video-clipper setup.');
  const env = runtimeEnvironment(root);
  if (command === 'init') {
    if (args.length !== 1) throw new Error('Usage: hermes-video-clipper init NEW_WORKSPACE_PATH');
    console.log(`Workspace created: ${initWorkspace(args[0], root)}\nOpen Hermes in this folder and read AGENTS.md.`);
    return;
  }
  if (command === 'test-python') {
    execute(python, ['-m', 'unittest', 'discover', '-s', path.join(root, 'tests'), '-v'], { root, env });
    return;
  }
  let workspace = process.cwd();
  const workspaceFlag = args.indexOf('--workspace');
  if (workspaceFlag >= 0) {
    if (!args[workspaceFlag + 1]) throw new Error('--workspace requires a path');
    workspace = path.resolve(args[workspaceFlag + 1]);
    args.splice(workspaceFlag, 2);
  }
  if (!fs.existsSync(path.join(workspace, 'config', 'channel.json')) || !fs.existsSync(path.join(workspace, 'scripts', 'clipping_pipeline.py'))) throw new Error('Not a clipper workspace. Run init or pass --workspace PATH.');
  if (command === 'doctor') {
    execute(python, ['-c', 'import faster_whisper, mediapipe, cv2; print("Local transcription/framing imports: OK")'], { root: workspace, env });
    const assets = ['whisper-small/model.bin', 'blaze_face_full_range_sparse.tflite'];
    for (const asset of assets) if (!fs.existsSync(path.join(workspace, 'assets', 'models', asset))) throw new Error(`Missing model: ${asset}`);
    execute(process.execPath, [path.join(root, 'node_modules', 'hyperframes', 'dist', 'cli.js'), 'browser', 'path'], { root: workspace, env });
    execute(python, [path.join(workspace, 'scripts', 'clip_library.py'), 'doctor'], { root: workspace, env });
    console.log('Installed runtime verified. Source rights and editorial/framing/audio review still require the agent.');
  } else {
    if (!args.length) throw new Error(`${command} requires stage/job arguments. See --help.`);
    const script = command === 'retention' ? 'retention_report.py' : 'clipping_pipeline.py';
    execute(python, [path.join(workspace, 'scripts', script), ...args], { root: workspace, env });
  }
}

main().catch(error => { console.error(`Hermes Video Clipper: ${error.message}`); process.exitCode = 1; });
