import { tool } from 'ai';
import { z } from 'zod';

export const MAX_TEXT_CHARS = 12_000;

export const FETCH_TIMEOUT_MS = 15_000;

export type FetchedPage = {
  title: string | undefined;
  text: string;
  truncated: boolean;
};

export function htmlToText(html: string): string {
  return html
    .replace(/<head\b[^>]*>[\s\S]*?<\/head>/gi, ' ')
    .replace(/<title\b[^>]*>[\s\S]*?<\/title>/gi, ' ')
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, ' ')
    .replace(/<noscript\b[^>]*>[\s\S]*?<\/noscript>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(p|div|section|article|header|footer|main|h[1-6]|li|tr|blockquote)>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/&amp;/gi, '&')
    .replace(/[ \t\f\v]+/g, ' ')
    .replace(/ *\n */g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function extractTitle(html: string): string | undefined {
  const match = html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i);
  const title = match?.[1] && htmlToText(match[1]);

  return title || undefined;
}

function truncate(text: string, maxChars: number): { text: string; truncated: boolean } {
  if (text.length <= maxChars) {
    return { text, truncated: false };
  }

  return {
    text: `${text.slice(0, maxChars)}...[truncated at ${maxChars} chars]`,
    truncated: true,
  };
}

export async function fetchUrl(
  url: string,
  options: { signal?: AbortSignal; maxChars?: number } = {},
): Promise<FetchedPage> {
  const maxChars = options.maxChars ?? MAX_TEXT_CHARS;

  const response = await fetch(url, {
    signal: options.signal ?? AbortSignal.timeout(FETCH_TIMEOUT_MS),
    redirect: 'follow',
    headers: { 'user-agent': 'research-agent/1.0' },
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.statusText}`.trim());
  }

  const contentType = response.headers.get('content-type') ?? '';
  const body = await response.text();
  const isHtml = contentType.includes('html');

  const { text, truncated } = truncate(isHtml ? htmlToText(body) : body.trim(), maxChars);

  return { title: isHtml ? extractTitle(body) : undefined, text, truncated };
}

export const fetchUrlTool = tool({
  description:
    'Download a single web page and return its readable text. Use when you have a specific URL ' +
    'to read. Returns the page title and body text, truncated at 12000 characters. ' +
    'Pages that render their content with JavaScript may return little or no text.',
  inputSchema: z.object({
    url: z.url().describe('absolute http(s) URL to read'),
  }),
  execute: async ({ url }, { abortSignal }) => {
    try {
      const page = await fetchUrl(url, { signal: abortSignal });

      return { ok: true, url, ...page };
    } catch (error) {
      return {
        ok: false,
        url,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  },
});
