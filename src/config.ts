import 'dotenv/config';
import { z } from 'zod';
import { parseEnv } from './env.js';

const parsed = parseEnv();

if (!parsed.success) {
  console.error('Invalid environment configuration:');
  console.error(z.prettifyError(parsed.error));
  process.exit(1);
}

const config = parsed.data;

export default config;
