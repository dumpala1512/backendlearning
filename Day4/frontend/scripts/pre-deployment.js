#!/usr/bin/env node
/**
 * ==============================================================================
 * Pre-deployment Safety Gate Script for Next.js Frontend
 *
 * Enforces two mandatory validation steps before the application build begins:
 *   1. Environment Variable Validation: Checks all required client-side
 *      (NEXT_PUBLIC_*) and server-side variables in process.env. Collects every
 *      missing variable and reports them before exiting with code 1.
 *   2. Backend Health Check: Performs a real HTTP GET request against the
 *      backend /health endpoint. Identifies connection timeouts, refused
 *      connections, or bad status codes and exits with code 1.
 * ==============================================================================
 */

'use strict';

console.log('================================================================================');
console.log('=== [Pre-deployment] Starting Frontend Safety Gate Validation               ===');
console.log('================================================================================');

// ------------------------------------------------------------------------------
// 1. Environment Variable Validation
// ------------------------------------------------------------------------------
console.log('=== [Check 1/2] Validating required environment variables ===');

const REQUIRED_VARIABLES = [
  { name: 'NEXT_PUBLIC_API_URL', scope: 'client', description: 'Backend API base URL' },
  { name: 'PORT', scope: 'server', description: 'Frontend server listen port' },
  { name: 'NODE_ENV', scope: 'server', description: 'Node environment mode' },
];

const missingVariables = [];

for (const variable of REQUIRED_VARIABLES) {
  const value = process.env[variable.name];
  if (value === undefined || value === null || value.trim() === '') {
    missingVariables.push(variable);
  }
}

if (missingVariables.length > 0) {
  console.error('\n[Pre-deployment] FATAL: Missing required environment variable(s):');
  for (const missing of missingVariables) {
    console.error(`  - ${missing.name} [${missing.scope.toUpperCase()}] (${missing.description})`);
  }
  console.error(
    `\n[Pre-deployment] Validation failed: ${missingVariables.length} required environment variable(s) must be defined before building.`
  );
  process.exit(1);
}

console.log('[Pre-deployment] SUCCESS: All required environment variables are present and configured:');
for (const variable of REQUIRED_VARIABLES) {
  console.log(`  - ${variable.name} [${variable.scope}]: ${process.env[variable.name]}`);
}

// ------------------------------------------------------------------------------
// 2. Backend Health Check
// ------------------------------------------------------------------------------
async function checkBackendHealth() {
  const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || '';
  const cleanApiUrl = rawApiUrl.replace(/\/+$/, '');
  const healthEndpoint = `${cleanApiUrl}/health`;

  console.log(`\n=== [Check 2/2] Verifying backend API health (${healthEndpoint}) ===`);

  // Optional bypass flag for isolated/offline build environments (e.g., Docker image compilation)
  if (
    process.env.SKIP_BACKEND_HEALTH_CHECK === 'true' ||
    process.env.SKIP_HEALTH_CHECK === 'true'
  ) {
    console.log(
      '[Pre-deployment] NOTICE: Backend health check skipped via SKIP_BACKEND_HEALTH_CHECK=true.'
    );
    return;
  }

  const timeoutMs = 6000;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(healthEndpoint, {
      method: 'GET',
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      console.error(
        `[Pre-deployment] FATAL: Backend health check failed at '${healthEndpoint}'. Returned HTTP ${response.status} ${response.statusText}.`
      );
      process.exit(1);
    }

    console.log(
      `[Pre-deployment] SUCCESS: Backend API is reachable and healthy at '${healthEndpoint}' (HTTP ${response.status}).`
    );
  } catch (err) {
    clearTimeout(timeoutId);
    let descriptiveError = err.message || 'Unknown network error';

    if (err.name === 'AbortError') {
      descriptiveError = `Connection timed out after ${timeoutMs}ms`;
    } else if (err.cause) {
      if (err.cause.code === 'ECONNREFUSED') {
        descriptiveError = `Connection refused (service appears to be offline or port is closed)`;
      } else if (err.cause.code) {
        descriptiveError = `${err.message} (${err.cause.code})`;
      }
    }

    console.error(
      `[Pre-deployment] FATAL: Failed to reach backend API at '${healthEndpoint}': ${descriptiveError}`
    );
    console.error(
      `[Pre-deployment] Validation failed: The backend service must be running and healthy before frontend build can proceed.`
    );
    process.exit(1);
  }
}

// Execute the async health check
checkBackendHealth().then(() => {
  console.log('\n================================================================================');
  console.log('=== [Pre-deployment] SUCCESS: All pre-deployment safety checks passed!       ===');
  console.log('================================================================================\n');
  process.exit(0);
});

