import { z } from 'zod';

export const envSchema = z.object({
  gemini_api_key: z.string().min(1),
  groq_api_key: z.string().min(1),
});

export type Config = z.infer<typeof envSchema>;

export function parseEnv(source: Record<string, string | undefined> = process.env) {
  return envSchema.safeParse({
    gemini_api_key: source.GEMINI_API_KEY,
    groq_api_key: source.GROQ_API_KEY,
  });
}
