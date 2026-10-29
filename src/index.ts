import config from './config.js';
import { ask } from './agent.js';

const question = process.argv.slice(2).join(' ') || 'Explain how an AI agent works.';

const text = await ask(question);

console.log(text);
