import config from './config.js';
import { ask } from './agent.js';
import { fetchUrlTool } from './tools/fetch-url.js';

const question = process.argv.slice(2).join(' ') || 'Explain how an AI agent works.';

const text = await ask(question, { tools: { fetch_url: fetchUrlTool } });

console.log(text);
