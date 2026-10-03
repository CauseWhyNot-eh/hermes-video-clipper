const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');

test('CLI explains agent-led usage and rejects unknown commands', () => {
  const cli = path.join(root, 'bin', 'cli.cjs');
  assert.ok(fs.existsSync(cli), 'Installable CLI is missing');
  const help = spawnSync(process.execPath, [cli, '--help'], { encoding: 'utf8' });
  assert.equal(help.status, 0);
  assert.match(help.stdout, /Hermes Video Clipper/);
  assert.match(help.stdout, /agent-led/);
  const invalid = spawnSync(process.execPath, [cli, 'not-a-command'], { encoding: 'utf8' });
  assert.equal(invalid.status, 1);
  assert.match(invalid.stderr, /Unknown command/);
});
