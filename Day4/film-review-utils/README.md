# @dumpala1512/env-validator

A lightweight, zero-dependency environment variable validator and schema parser for modern TypeScript, Node.js, and browser applications. Consumable via both ES Modules (ESM) and CommonJS (CJS).

## Features

- **Dual Module Support**: Full support for both ESM (`import`) and CommonJS (`require`).
- **Complete Type Safety**: Emits TypeScript definitions (`.d.ts`) with autocomplete and compile-time validation.
- **Built-in Type Parsers**: Automatically validates and parses `string`, `number`, `boolean`, `url`, `port`, and `enum`.
- **Scope Categorization**: Tag variables with `'client'`, `'server'`, or `'shared'` for pre-deployment validation gates.
- **Detailed Reporting**: Built-in CLI report formatter (`formatValidationReport`) for pre-build safety gates and CI/CD pipelines.
- **Zero Runtime Dependencies**: Ultra lightweight and fast.

## Installation

```bash
# npm
npm install @dumpala1512/env-validator

# pnpm
pnpm add @dumpala1512/env-validator

# yarn
yarn add @dumpala1512/env-validator

# bun
bun add @dumpala1512/env-validator
```

## Quick Start

### ES Modules (TypeScript / Next.js / Vite)

```typescript
import { validateEnv, defineEnvSchema, formatValidationReport } from "@dumpala1512/env-validator";

const envSchema = defineEnvSchema({
  NEXT_PUBLIC_API_URL: {
    name: "NEXT_PUBLIC_API_URL",
    type: "url",
    scope: "client",
    description: "Backend API base URL",
  },
  PORT: {
    name: "PORT",
    type: "port",
    scope: "server",
    default: 3000,
  },
  NODE_ENV: {
    name: "NODE_ENV",
    type: "enum",
    enumValues: ["development", "production", "test"],
    default: "development",
  },
});

const result = validateEnv(envSchema, process.env);

if (!result.isValid) {
  console.error(formatValidationReport(result));
  process.exit(1);
}

console.log(formatValidationReport(result));
```

### CommonJS (Node.js Scripts / Build Tools)

```javascript
const { validateEnv, defineEnvSchema, formatValidationReport } = require("@dumpala1512/env-validator");

const schema = defineEnvSchema({
  DATABASE_URL: { name: "DATABASE_URL", type: "string", required: true },
  PORT: { name: "PORT", type: "port", default: 8080 },
});

const result = validateEnv(schema, process.env);
if (!result.isValid) {
  console.error(result.summary);
  process.exit(1);
}
```

## API Reference

### `validateEnv(definitions, source?, options?)`

- `definitions`: Array of `EnvVarDefinition` or an object schema created with `defineEnvSchema`.
- `source`: Key-value object of environment variables (defaults to `process.env`).
- `options`:
  - `throwOnError` (boolean): Throws `EnvValidationError` if validation fails.
  - `silent` (boolean): Suppresses internal logging.

Returns a `ValidationResult<T>`:
```typescript
interface ValidationResult<T> {
  isValid: boolean;
  data: T;
  missing: MissingEnvVar[];
  invalid: InvalidEnvVar[];
  summary: string;
}
```

### Supported Types

- `'string'`: Non-empty string.
- `'number'`: Parsed via `Number()`, rejected if `NaN`.
- `'port'`: Integer between 1 and 65535.
- `'boolean'`: Accepts `'true'`, `'1'`, `'yes'` as `true`; `'false'`, `'0'`, `'no'` as `false`.
- `'url'`: Validated using the standard `URL` constructor.
- `'enum'`: Must match one of `enumValues`.

## License

MIT
