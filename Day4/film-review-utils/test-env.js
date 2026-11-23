const { validateEnv, defineEnvSchema, formatValidationReport } = require('./dist/cjs/index.js');

// Define the expected schema for your environment variables
const schema = defineEnvSchema({
  NEXT_PUBLIC_API_URL: {
    name: 'NEXT_PUBLIC_API_URL',
    type: 'url',
    scope: 'client',
    description: 'Backend API Base URL',
    required: true,
  },
  PORT: {
    name: 'PORT',
    type: 'port',
    scope: 'server',
    description: 'Frontend server port',
    default: 3000,
  },
  NODE_ENV: {
    name: 'NODE_ENV',
    type: 'enum',
    enumValues: ['development', 'production', 'test'],
    scope: 'server',
    default: 'development',
  },
});

console.log('--- Testing .env with validateEnv ---');
const result = validateEnv(schema, process.env);
console.log(formatValidationReport(result));

if (!result.isValid) {
  process.exitCode = 1;
}
