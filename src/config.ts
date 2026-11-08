import dotenv from 'dotenv';
dotenv.config();
import { z } from 'zod';

const envSchema = z.object({
  searxng_url: z.string().min(1),
  gemini_api_key: z.string().min(1),
  groq_api_key: z.string().min(1),
});

function parseEnv(source: Record<string, string | undefined> = process.env) {
  return envSchema.safeParse({
    searxng_url: source.SEARXNG_URL,
    gemini_api_key: source.GEMINI_API_KEY,
    groq_api_key: source.GROQ_API_KEY,
  });
}

const parsed = parseEnv();

if (!parsed.success) {
  console.error('Invalid environment configuration:');
  console.error(z.prettifyError(parsed.error));
  process.exit(1);
}

const config = parsed.data;

export default config;
