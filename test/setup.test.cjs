const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const http = require('node:http');
const root = path.resolve(__dirname, '..');
const scratch = process.env.CLIPPING_SCRATCH || (process.env.HERMES_HOME ? path.join(process.env.HERMES_HOME, 'cache', 'scratch') : path.join(root, '.workflow', 'scratch'));
fs.mkdirSync(scratch, { recursive: true });

test('installer verifies download hashes and rejects mismatched content without replacing a file', async () => {
  const modulePath = path.join(root, 'bin', 'setup.cjs');
  assert.ok(fs.existsSync(modulePath), 'Verified runtime installer is missing');
  const { downloadVerified } = require(modulePath);
  const body = Buffer.from('explicit test fixture, not a model');
  const hash = crypto.createHash('sha256').update(body).digest('hex');
  const server = http.createServer((request, response) => response.end(body));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const temporary = fs.mkdtempSync(path.join(scratch, 'hvc-download-test-'));
  try {
    const target = path.join(temporary, 'asset.bin');
    const url = `http://127.0.0.1:${server.address().port}/asset`;
    await downloadVerified(url, target, hash);
    assert.deepEqual(fs.readFileSync(target), body);
    await assert.rejects(downloadVerified(url, target, '0'.repeat(64)), /SHA-256/);
    assert.deepEqual(fs.readFileSync(target), body);
    assert.equal(fs.readdirSync(temporary).length, 1);
  } finally {
    server.close();
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});
