const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const root = path.resolve(__dirname, '..');
const scratch = process.env.CLIPPING_SCRATCH || (process.env.HERMES_HOME ? path.join(process.env.HERMES_HOME, 'cache', 'scratch') : path.join(root, '.workflow', 'scratch'));
fs.mkdirSync(scratch, { recursive: true });

test('missing prerequisites do not leave a half-created workspace', () => {
  const { initWorkspace } = require(path.join(root, 'bin', 'runtime.cjs'));
  const temporary = fs.mkdtempSync(path.join(scratch, 'hvc-preflight-test-'));
  try {
    const target = path.join(temporary, 'workspace');
    assert.throws(() => initWorkspace(target, temporary));
    assert.equal(fs.existsSync(target), false);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

test('workspace creation preserves media and refuses overwriting an existing workspace', () => {
  const modulePath = path.join(root, 'bin', 'runtime.cjs');
  assert.ok(fs.existsSync(modulePath), 'Workspace initializer is missing');
  const { initWorkspace } = require(modulePath);
  const temporary = fs.mkdtempSync(path.join(scratch, 'hvc-init-test-'));
  try {
    const target = path.join(temporary, 'workspace');
    initWorkspace(target, root, { linkRuntime: false });
    assert.ok(fs.existsSync(path.join(target, 'config', 'channel.json')));
    assert.ok(fs.existsSync(path.join(target, 'skills', 'hermes-video-clipper', 'SKILL.md')));
    assert.ok(fs.existsSync(path.join(target, 'inputs', 'podcasts')));
    assert.ok(fs.existsSync(path.join(target, 'output', 'final')));
    const final = path.join(target, 'output', 'final', 'approved.mp4');
    fs.writeFileSync(final, 'fixture-only');
    assert.throws(() => initWorkspace(target, root, { linkRuntime: false }), /exists/);
    assert.equal(fs.readFileSync(final, 'utf8'), 'fixture-only');
    const config = JSON.parse(fs.readFileSync(path.join(target, 'config', 'channel.json')));
    assert.equal(config.automatic_publication, false);
    assert.deepEqual(config.music_preference.track_volume_overrides, {});
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});
