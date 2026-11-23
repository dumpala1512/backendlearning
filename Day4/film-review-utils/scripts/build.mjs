import { execSync } from 'node:child_process';
import { rmSync, existsSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = resolve(__dirname, '..');
const distDir = resolve(rootDir, 'dist');

console.log('[build] Cleaning previous dist output...');
if (existsSync(distDir)) {
  rmSync(distDir, { recursive: true, force: true });
}

let tscCmd = 'npx tsc';
const localTsc = resolve(rootDir, 'node_modules/.bin/tsc');
const parentTsc = resolve(rootDir, '../frontend/node_modules/typescript/bin/tsc');
if (existsSync(localTsc)) {
  tscCmd = `"${localTsc}"`;
} else if (existsSync(parentTsc)) {
  tscCmd = `node "${parentTsc}"`;
}

console.log('[build] Compiling ES Module build (dist/esm)...');
execSync(`${tscCmd} -p tsconfig.esm.json`, { cwd: rootDir, stdio: 'inherit' });
mkdirSync(resolve(distDir, 'esm'), { recursive: true });
writeFileSync(resolve(distDir, 'esm/package.json'), JSON.stringify({ type: 'module' }, null, 2));

console.log('[build] Compiling CommonJS build (dist/cjs)...');
execSync(`${tscCmd} -p tsconfig.cjs.json`, { cwd: rootDir, stdio: 'inherit' });
mkdirSync(resolve(distDir, 'cjs'), { recursive: true });
writeFileSync(resolve(distDir, 'cjs/package.json'), JSON.stringify({ type: 'commonjs' }, null, 2));

console.log('[build] Generating Type Declarations (dist/types)...');
execSync(`${tscCmd} -p tsconfig.types.json`, { cwd: rootDir, stdio: 'inherit' });

console.log('[build] SUCCESS: Dual ESM/CJS build completed successfully.');
