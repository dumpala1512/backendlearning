import test from 'node:test';
import assert from 'node:assert/strict';
import { validateEnv, defineEnvSchema, EnvValidationError, formatValidationReport } from '../dist/esm/index.js';

test('validateEnv should succeed when all required variables are valid', () => {
  const schema = defineEnvSchema({
    PORT: { name: 'PORT', type: 'port', scope: 'server', required: true },
    API_URL: { name: 'API_URL', type: 'url', scope: 'client', required: true },
    NODE_ENV: { name: 'NODE_ENV', type: 'enum', enumValues: ['development', 'production', 'test'], required: true },
    ENABLE_FEATURE: { name: 'ENABLE_FEATURE', type: 'boolean', required: false, default: false },
  });

  const source = {
    PORT: '8080',
    API_URL: 'http://localhost:8000',
    NODE_ENV: 'production',
  };

  const result = validateEnv(schema, source);

  assert.equal(result.isValid, true);
  assert.equal(result.missing.length, 0);
  assert.equal(result.invalid.length, 0);
  assert.equal(result.data.PORT, 8080);
  assert.equal(result.data.API_URL, 'http://localhost:8000');
  assert.equal(result.data.NODE_ENV, 'production');
  assert.equal(result.data.ENABLE_FEATURE, false);
});

test('validateEnv should detect missing required variables', () => {
  const schema = defineEnvSchema({
    REQUIRED_VAR: { name: 'REQUIRED_VAR', type: 'string', scope: 'server', description: 'Secret key' },
    OPTIONAL_VAR: { name: 'OPTIONAL_VAR', type: 'string', required: false },
  });

  const result = validateEnv(schema, {});

  assert.equal(result.isValid, false);
  assert.equal(result.missing.length, 1);
  assert.equal(result.missing[0].name, 'REQUIRED_VAR');
  assert.equal(result.missing[0].scope, 'server');
});

test('validateEnv should flag invalid port numbers', () => {
  const schema = [
    { name: 'PORT', type: 'port' },
  ];

  const result = validateEnv(schema, { PORT: '99999' });
  assert.equal(result.isValid, false);
  assert.equal(result.invalid.length, 1);
  assert.match(result.invalid[0].reason, /port/i);
});

test('validateEnv should flag invalid URLs', () => {
  const schema = [
    { name: 'NEXT_PUBLIC_API_URL', type: 'url' },
  ];

  const result = validateEnv(schema, { NEXT_PUBLIC_API_URL: 'not-a-valid-url' });
  assert.equal(result.isValid, false);
  assert.equal(result.invalid.length, 1);
  assert.match(result.invalid[0].reason, /URL/i);
});

test('validateEnv should flag invalid enums', () => {
  const schema = [
    { name: 'NODE_ENV', type: 'enum', enumValues: ['development', 'production', 'test'] },
  ];

  const result = validateEnv(schema, { NODE_ENV: 'staging' });
  assert.equal(result.isValid, false);
  assert.equal(result.invalid.length, 1);
  assert.match(result.invalid[0].reason, /Expected one of/);
});

test('validateEnv should support custom validators', () => {
  const schema = [
    {
      name: 'CUSTOM_KEY',
      type: 'string',
      validator: (val) => val.startsWith('key_') || 'Must start with key_',
    },
  ];

  const failResult = validateEnv(schema, { CUSTOM_KEY: 'invalid_prefix' });
  assert.equal(failResult.isValid, false);
  assert.equal(failResult.invalid[0].reason, 'Must start with key_');

  const passResult = validateEnv(schema, { CUSTOM_KEY: 'key_12345' });
  assert.equal(passResult.isValid, true);
});

test('validateEnv throwOnError should throw EnvValidationError', () => {
  const schema = [{ name: 'MISSING_SECRET', required: true }];

  assert.throws(
    () => {
      validateEnv(schema, {}, { throwOnError: true });
    },
    (err) => err instanceof EnvValidationError && err.missing.length === 1
  );
});

test('formatValidationReport should output clear text', () => {
  const schema = [
    { name: 'MISSING_VAR', required: true, scope: 'client', description: 'Test var' },
    { name: 'BAD_PORT', type: 'port', required: true },
  ];

  const result = validateEnv(schema, { BAD_PORT: 'invalid' });
  const report = formatValidationReport(result);

  assert.match(report, /FATAL/);
  assert.match(report, /MISSING_VAR/);
  assert.match(report, /BAD_PORT/);
});
