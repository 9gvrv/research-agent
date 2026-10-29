import { describe, expect, it } from 'vitest';
import { parseEnv } from '../src/env.js';

const valid = { GEMINI_API_KEY: 'gemini-key', GROQ_API_KEY: 'groq-key' };

describe('parseEnv', () => {
  it('accepts a complete environment', () => {
    const result = parseEnv(valid);

    expect(result.success).toBe(true);
    expect(result.data).toEqual({
      gemini_api_key: 'gemini-key',
      groq_api_key: 'groq-key',
    });
  });

  it('rejects a missing groq key', () => {
    const result = parseEnv({ GEMINI_API_KEY: 'gemini-key' });

    expect(result.success).toBe(false);
    expect(result.error?.issues.map((issue) => issue.path[0])).toEqual(['groq_api_key']);
  });

  it('rejects an empty key', () => {
    const result = parseEnv({ ...valid, GROQ_API_KEY: '' });

    expect(result.success).toBe(false);
    expect(result.error?.issues).toHaveLength(1);
  });

  it('reports every missing key at once', () => {
    const result = parseEnv({});

    expect(result.success).toBe(false);
    expect(result.error?.issues.map((issue) => issue.path[0]).sort()).toEqual([
      'gemini_api_key',
      'groq_api_key',
    ]);
  });
});
