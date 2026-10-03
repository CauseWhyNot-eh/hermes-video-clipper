const fs = require('node:fs');
const path = require('node:path');

function initWorkspace(destination, packageRoot, { linkRuntime = true } = {}) {
  const target = path.resolve(destination);
  if (fs.existsSync(target)) throw new Error('Workspace already exists; refusing to overwrite it. Choose a new empty path.');
  const templates = ['scripts', 'config', 'skills', 'assets/fonts', 'AGENTS.md', 'WORKFLOW.md', 'CUSTOM_CLIPPING.md', '.hermes.md'];
  const links = linkRuntime ? ['.clipping-venv', 'assets/models', 'tools/hyperframes'] : [];
  for (const item of [...templates, ...links]) {
    if (!fs.existsSync(path.join(packageRoot, item))) throw new Error(`Missing prerequisite: ${item}. Run setup before creating a workspace.`);
  }
  fs.mkdirSync(target, { recursive: true });
  for (const item of ['scripts', 'config', 'skills', 'AGENTS.md', 'WORKFLOW.md', 'CUSTOM_CLIPPING.md', '.hermes.md']) {
    fs.cpSync(path.join(packageRoot, item), path.join(target, item), { recursive: true });
  }
  fs.mkdirSync(path.join(target, 'assets'), { recursive: true });
  fs.cpSync(path.join(packageRoot, 'assets', 'fonts'), path.join(target, 'assets', 'fonts'), { recursive: true });
  for (const item of ['inputs/podcasts', 'inputs/clips', 'inputs/music', 'output/final', 'library/manifests', '.workflow']) {
    fs.mkdirSync(path.join(target, item), { recursive: true });
  }
  if (linkRuntime) {
    for (const item of ['.clipping-venv', 'assets/models', 'tools/hyperframes']) {
      const source = path.join(packageRoot, item);
      if (!fs.existsSync(source)) throw new Error(`Runtime missing: ${item}. Run hermes-video-clipper setup first.`);
      fs.mkdirSync(path.dirname(path.join(target, item)), { recursive: true });
      fs.symlinkSync(source, path.join(target, item), 'junction');
    }
  }
  fs.writeFileSync(path.join(target, 'STATUS.md'), '# Workspace status\n\nNo source processed yet. Run doctor and inspect actual files before starting.\n');
  return target;
}

module.exports = { initWorkspace };
