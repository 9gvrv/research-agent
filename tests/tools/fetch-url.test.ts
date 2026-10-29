import { afterEach, describe, expect, it, vi } from 'vitest';
import { extractTitle, fetchUrl, htmlToText } from '../../src/tools/fetch-url.js';

function htmlResponse(body: string, status = 200) {
  return new Response(body, { status, headers: { 'content-type': 'text/html' } });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('htmlToText', () => {
  it('drops script, style and comment content', () => {
    const html = `
      <html><head><style>.a { color: red }</style></head>
      <body><!-- hidden --><script>alert('x')</script><p>Visible text</p></body></html>`;

    const text = htmlToText(html);

    expect(text).toBe('Visible text');
    expect(text).not.toContain('color: red');
    expect(text).not.toContain('alert');
    expect(text).not.toContain('hidden');
  });

  it('keeps paragraph breaks but collapses runs of blank lines', () => {
    const text = htmlToText('<p>one</p><p>two</p><p>three</p>');

    expect(text).toBe('one\ntwo\nthree');
  });

  it('decodes common entities', () => {
    expect(htmlToText('<p>a &amp; b &lt;c&gt; &quot;d&quot; &#39;e&#39;</p>')).toBe(
      `a & b <c> "d" 'e'`,
    );
  });

  it('collapses horizontal whitespace', () => {
    expect(htmlToText('<p>a      b\t\tc</p>')).toBe('a b c');
  });
});

describe('extractTitle', () => {
  it('returns a cleaned title', () => {
    expect(extractTitle('<title>  Hello   World </title>')).toBe('Hello World');
  });

  it('returns undefined when there is no title', () => {
    expect(extractTitle('<p>no title</p>')).toBeUndefined();
  });
});

describe('fetchUrl', () => {
  it('returns the readable text of an HTML page', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        htmlResponse('<html><title>Docs</title><body><p>Hello there</p></body></html>'),
      ),
    );

    const page = await fetchUrl('https://example.com');

    expect(page).toEqual({ title: 'Docs', text: 'Hello there', truncated: false });
  });

  it('leaves non-HTML bodies unstripped', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('plain words', { status: 200 })),
    );

    const page = await fetchUrl('https://example.com/file.txt');

    expect(page).toEqual({ title: undefined, text: 'plain words', truncated: false });
  });

  it('throws on a non-2xx response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => htmlResponse('nope', 404)),
    );

    await expect(fetchUrl('https://example.com/missing')).rejects.toThrow('HTTP 404');
  });

  it('truncates long text and says so', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('word '.repeat(100), { status: 200 })),
    );

    const page = await fetchUrl('https://example.com', { maxChars: 20 });

    expect(page.truncated).toBe(true);
    expect(page.text).toContain('[truncated at 20 chars]');
    expect(page.text.startsWith('word word word word ')).toBe(true);
  });
});
