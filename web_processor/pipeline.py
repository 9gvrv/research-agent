import asyncio
import hashlib

import httpx

from .cleaner import clean_document
from .extractor import extract
from .fetcher import DEFAULT_HEADERS, fetch
from .models import Document

# One shared connection pool instead of a client (and TLS handshake) per URL.
CONCURRENCY = 8
TIMEOUT = 20.0


async def process_url(
    url: str,
    client: httpx.AsyncClient | None = None,
) -> Document | None:
    if client is not None:
        return await _process(url, client)

    async with httpx.AsyncClient(
        headers=DEFAULT_HEADERS,
        timeout=TIMEOUT,
        follow_redirects=True,
    ) as own_client:
        return await _process(url, own_client)


async def process_urls(
    urls: list[str],
    concurrency: int = CONCURRENCY,
) -> list[Document]:

    # Search queries often return the same URL more than once.
    urls = list(dict.fromkeys(urls))

    limits = httpx.Limits(
        max_connections=concurrency,
        max_keepalive_connections=concurrency,
    )
    async with httpx.AsyncClient(
        headers=DEFAULT_HEADERS,
        timeout=TIMEOUT,
        follow_redirects=True,
        limits=limits,
    ) as client:
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded(url: str) -> Document | None:
            async with semaphore:
                return await _process(url, client)

        results = await asyncio.gather(*(bounded(url) for url in urls))

    documents = [document for document in results if document is not None]
    return _dedupe(documents)


async def _process(url: str, client: httpx.AsyncClient) -> Document | None:
    try:
        html = await fetch(client, url)

        document = extract(
            html,
            url,
        )

        if document is None:
            return None

        return clean_document(document)

    except Exception as e:
        print(f"Failed to process {url}: {e}")

        return None


def _dedupe(documents: list[Document]) -> list[Document]:
    """Drop the same article served under more than one URL."""
    by_lead: dict[str, list[tuple[str, str]]] = {}
    unique: list[Document] = []

    for document in documents:
        body = "\n".join(section.content for section in document.sections)
        lead = _sha1(body[:400])
        full = _sha1(body)
        title = _sha1((document.title or "").casefold())

        prior = by_lead.setdefault(lead, [])
        if any(
            full == p_full or (document.title and title == p_title)
            for p_full, p_title in prior
        ):
            continue

        prior.append((full, title))
        unique.append(document)

    return unique


def _sha1(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", "ignore")).hexdigest()
