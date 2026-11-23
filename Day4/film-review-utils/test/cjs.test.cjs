const test = require('node:test');
const assert = require('node:assert/strict');
const { validateEnv, defineEnvSchema, formatValidationReport } = require('../dist/cjs/index.js');

test('CommonJS: require("@dumpala1512/env-validator") works as expected', () => {
  const schema = defineEnvSchema({
    PORT: { name: 'PORT', type: 'port', default: 3000 },
  });

  const result = validateEnv(schema, {});
  assert.equal(result.isValid, true);
  assert.equal(result.data.PORT, 3000);
});
