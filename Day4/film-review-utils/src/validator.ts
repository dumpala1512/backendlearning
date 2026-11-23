import {
  EnvVarDefinition,
  EnvVarScope,
  InvalidEnvVar,
  MissingEnvVar,
  ValidateEnvOptions,
  ValidationResult,
} from './types.js';

declare const process: any;

export class EnvValidationError extends Error {
  public readonly missing: MissingEnvVar[];
  public readonly invalid: InvalidEnvVar[];

  constructor(message: string, missing: MissingEnvVar[] = [], invalid: InvalidEnvVar[] = []) {
    super(message);
    this.name = 'EnvValidationError';
    this.missing = missing;
    this.invalid = invalid;
    Object.setPrototypeOf(this, EnvValidationError.prototype);
  }
}

/**
 * Type-safe helper for declaring environment variable schemas.
 */
export function defineEnvSchema<T extends Record<string, EnvVarDefinition>>(
  schema: T
): T {
  return schema;
}

/**
 * Parses and validates an individual environment variable value.
 */
function parseAndValidateValue(
  def: EnvVarDefinition,
  rawValue: string
): { value: any; error?: string } {
  const type = def.type || 'string';

  switch (type) {
    case 'number': {
      const num = Number(rawValue);
      if (isNaN(num)) {
        return { value: rawValue, error: `Expected a valid number, got '${rawValue}'` };
      }
      return { value: num };
    }

    case 'port': {
      const port = Number(rawValue);
      if (!Number.isInteger(port) || port < 1 || port > 65535) {
        return { value: rawValue, error: `Expected an integer port between 1 and 65535, got '${rawValue}'` };
      }
      return { value: port };
    }

    case 'boolean': {
      const lower = rawValue.trim().toLowerCase();
      if (lower === 'true' || lower === '1' || lower === 'yes') {
        return { value: true };
      }
      if (lower === 'false' || lower === '0' || lower === 'no') {
        return { value: false };
      }
      return { value: rawValue, error: `Expected a boolean (true/false/1/0), got '${rawValue}'` };
    }

    case 'url': {
      try {
        const parsed = new URL(rawValue);
        if (!parsed.protocol || !parsed.host) {
          return { value: rawValue, error: `Invalid URL structure: '${rawValue}'` };
        }
        return { value: rawValue };
      } catch {
        return { value: rawValue, error: `Invalid URL format: '${rawValue}'` };
      }
    }

    case 'enum': {
      if (def.enumValues && !def.enumValues.includes(rawValue)) {
        return {
          value: rawValue,
          error: `Expected one of [${def.enumValues.join(', ')}], got '${rawValue}'`,
        };
      }
      return { value: rawValue };
    }

    case 'string':
    default: {
      return { value: rawValue };
    }
  }
}

/**
 * Validates environment variables against a schema of definitions.
 *
 * @param definitions Array or map of variable definitions
 * @param source Optional source object (defaults to process.env)
 * @param options Validation options (e.g. throwOnError)
 */
export function validateEnv<T extends Record<string, any> = Record<string, any>>(
  definitions: EnvVarDefinition[] | Record<string, EnvVarDefinition>,
  source: Record<string, string | undefined> = typeof process !== 'undefined' ? process.env : {},
  options: ValidateEnvOptions = {}
): ValidationResult<T> {
  const defsList: EnvVarDefinition[] = Array.isArray(definitions)
    ? definitions
    : Object.entries(definitions).map(([key, def]) => ({
        ...def,
        name: def.name || key,
      }));

  const missing: MissingEnvVar[] = [];
  const invalid: InvalidEnvVar[] = [];
  const data: Record<string, any> = {};

  for (const def of defsList) {
    const rawValue = source[def.name];
    const isPresent = rawValue !== undefined && rawValue !== null && rawValue.trim() !== '';

    if (!isPresent) {
      if (def.default !== undefined) {
        data[def.name] = def.default;
      } else if (def.required !== false) {
        missing.push({
          name: def.name,
          scope: def.scope,
          description: def.description,
        });
      }
      continue;
    }

    // Parse and validate value
    const { value, error } = parseAndValidateValue(def, rawValue!);

    if (error) {
      invalid.push({
        name: def.name,
        value: rawValue,
        reason: error,
        scope: def.scope,
      });
      continue;
    }

    // Run custom validator if supplied
    if (def.validator) {
      const customValidation = def.validator(value);
      if (customValidation === false || typeof customValidation === 'string') {
        const reason = typeof customValidation === 'string'
          ? customValidation
          : `Custom validator rejected value '${rawValue}'`;
        invalid.push({
          name: def.name,
          value,
          reason,
          scope: def.scope,
        });
        continue;
      }
    }

    data[def.name] = value;
  }

  const isValid = missing.length === 0 && invalid.length === 0;
  const summary = isValid
    ? `All ${defsList.length} environment variables successfully validated.`
    : `Validation failed: ${missing.length} missing, ${invalid.length} invalid variable(s).`;

  const result: ValidationResult<T> = {
    isValid,
    data: data as T,
    missing,
    invalid,
    summary,
  };

  if (!isValid && options.throwOnError) {
    throw new EnvValidationError(summary, missing, invalid);
  }

  return result;
}
