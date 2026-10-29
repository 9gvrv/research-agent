import { describe, expect, it } from 'vitest';
import { MockLanguageModelV4 } from 'ai/test';
import { ask, DEFAULT_MODEL_ID } from '../src/agent.js';

function mockModel(text: string) {
  const calls: unknown[] = [];

  const model = new MockLanguageModelV4({
    doGenerate: async (options) => {
      calls.push(options);

      return {
        content: [{ type: 'text', text }],
        finishReason: { unified: 'stop', raw: undefined },
        usage: {
          inputTokens: { total: 10, noCache: 10, cacheRead: undefined, cacheWrite: undefined },
          outputTokens: { total: 20, text: 20, reasoning: undefined },
        },
        warnings: [],
      };
    },
  });

  return { model, calls };
}

describe('ask', () => {
  it('returns the model text', async () => {
    const { model } = mockModel('An agent perceives, decides, and acts.');

    await expect(ask('What is an agent?', { model })).resolves.toBe(
      'An agent perceives, decides, and acts.',
    );
  });

  it('forwards the question as the prompt', async () => {
    const { model, calls } = mockModel('ok');

    await ask('Why do agents loop?', { model });

    expect(calls).toHaveLength(1);
    expect(JSON.stringify(calls[0])).toContain('Why do agents loop?');
  });

  it('surfaces provider failures to the caller', async () => {
    const model = new MockLanguageModelV4({
      doGenerate: async () => {
        throw new Error('rate limited');
      },
    });

    await expect(ask('anything', { model })).rejects.toThrow('rate limited');
  });

  it('defaults to the free Groq model', () => {
    expect(DEFAULT_MODEL_ID).toBe('openai/gpt-oss-120b');
  });
});
