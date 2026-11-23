import { ValidationResult } from './types.js';

/**
 * Formats a validation result into a human-readable CLI report.
 */
export function formatValidationReport(result: ValidationResult): string {
  const lines: string[] = [];

  if (result.isValid) {
    lines.push('[Validation] SUCCESS: All required environment variables are configured.');
    for (const [key, val] of Object.entries(result.data)) {
      lines.push(`  - ${key}: ${String(val)}`);
    }
    return lines.join('\n');
  }

  lines.push('[Validation] FATAL: Environment validation failed!');

  if (result.missing.length > 0) {
    lines.push('\nMissing required variables:');
    for (const item of result.missing) {
      const scopeTag = item.scope ? ` [${item.scope.toUpperCase()}]` : '';
      const desc = item.description ? ` (${item.description})` : '';
      lines.push(`  - ${item.name}${scopeTag}${desc}`);
    }
  }

  if (result.invalid.length > 0) {
    lines.push('\nInvalid variables:');
    for (const item of result.invalid) {
      const scopeTag = item.scope ? ` [${item.scope.toUpperCase()}]` : '';
      lines.push(`  - ${item.name}${scopeTag}: ${item.reason} (received: '${item.value}')`);
    }
  }

  return lines.join('\n');
}
