const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const HEALTH_URL = process.env.REACT_APP_API_HEALTH_URL || 'http://localhost:8000/health';
const BACKEND_START_SCRIPT = path.resolve(__dirname, '../../../backend/start_backend.sh');
const MAX_WAIT_MS = 30000;
const POLL_INTERVAL_MS = 1000;

function checkHealth(url) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: 1500 }, (res) => {
      res.resume();
      resolve(res.statusCode && res.statusCode >= 200 && res.statusCode < 500);
    });

    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

function startBackend() {
  const child = spawn('bash', [BACKEND_START_SCRIPT], {
    detached: true,
    stdio: 'ignore',
    cwd: path.resolve(__dirname, '../../../backend'),
  });

  child.unref();
}

async function waitUntilHealthy() {
  const start = Date.now();

  while (Date.now() - start < MAX_WAIT_MS) {
    const healthy = await checkHealth(HEALTH_URL);
    if (healthy) {
      return true;
    }

    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }

  return false;
}

(async () => {
  if (process.env.SKIP_BACKEND_ENSURE === '1') {
    console.log('[ensure-backend] Skipping backend health check (SKIP_BACKEND_ENSURE=1)');
    process.exit(0);
  }

  const alreadyRunning = await checkHealth(HEALTH_URL);

  if (alreadyRunning) {
    console.log('[ensure-backend] Backend is already running on localhost:8000');
    process.exit(0);
  }

  console.log('[ensure-backend] Backend is not running. Starting backend...');
  startBackend();

  const ready = await waitUntilHealthy();

  if (!ready) {
    console.error('[ensure-backend] Backend did not become healthy within 30s.');
    console.error('[ensure-backend] Check backend logs in backend/backend.log');
    process.exit(1);
  }

  console.log('[ensure-backend] Backend is healthy. Starting frontend...');
  process.exit(0);
})();
