export type EnvVarType = 'string' | 'number' | 'boolean' | 'url' | 'port' | 'enum';

export type EnvVarScope = 'client' | 'server' | 'shared';

export interface EnvVarDefinition<T = any> {
  name: string;
  type?: EnvVarType;
  scope?: EnvVarScope;
  description?: string;
  required?: boolean;
  default?: T;
  enumValues?: readonly string[];
  validator?: (value: any) => boolean | string;
}

export interface MissingEnvVar {
  name: string;
  scope?: EnvVarScope;
  description?: string;
}

export interface InvalidEnvVar {
  name: string;
  value: any;
  reason: string;
  scope?: EnvVarScope;
}

export interface ValidationResult<T = Record<string, any>> {
  isValid: boolean;
  data: T;
  missing: MissingEnvVar[];
  invalid: InvalidEnvVar[];
  summary: string;
}

export interface ValidateEnvOptions {
  /**
   * If true, throws EnvValidationError when validation fails.
   * Default: false
   */
  throwOnError?: boolean;
  /**
   * Optional custom logger or silent flag.
   */
  silent?: boolean;
}
