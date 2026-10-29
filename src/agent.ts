import { groq } from '@ai-sdk/groq';
import { generateText, stepCountIs, type LanguageModel, type ToolSet } from 'ai';

export const DEFAULT_MODEL_ID = 'openai/gpt-oss-120b';

export const MAX_STEPS = 5;

export type AskOptions = {
  model?: LanguageModel;
  tools?: ToolSet;
};

export async function ask(question: string, options: AskOptions = {}) {
  const { text } = await generateText({
    model: options.model ?? groq(DEFAULT_MODEL_ID),
    tools: options.tools,
    stopWhen: stepCountIs(MAX_STEPS),
    prompt: question,
  });

  return text;
}
