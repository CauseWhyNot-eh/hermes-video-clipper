const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');

test('npm tarball excludes runtime, private media and Python bytecode', { skip: !process.env.npm_execpath }, () => {
  const result = spawnSync(process.execPath, [process.env.npm_execpath, 'pack', '--dry-run', '--json'], { cwd: root, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  const names = JSON.parse(result.stdout)[0].files.map(file => file.path);
  assert.ok(names.includes('skills/hermes-video-clipper/SKILL.md'));
  assert.ok(names.includes('bin/cli.cjs'));
  for (const name of names) {
    assert.doesNotMatch(name, /(^|\/)(inputs|output|library|\.runtime|\.workflow|\.clipping-venv|__pycache__)(\/|$)|\.pyc$/);
    assert.doesNotMatch(name, /^assets\/(models|music)\//);
  }
});
