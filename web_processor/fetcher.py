import httpx

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Pages are article-sized; anything bigger is a download or an infinite feed.
MAX_BYTES = 2_000_000
_ALLOWED_CONTENT_TYPES = ("text/", "application/xhtml", "application/xml", "+xml")


async def fetch(client: httpx.AsyncClient, url: str) -> str:
    async with client.stream("GET", url) as response:
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if content_type and not any(
            allowed in content_type for allowed in _ALLOWED_CONTENT_TYPES
        ):
            raise ValueError(f"unsupported content type {content_type!r}")

        chunks: list[bytes] = []
        received = 0
        async for chunk in response.aiter_bytes():
            received += len(chunk)
            if received > MAX_BYTES:
                break
            chunks.append(chunk)

        encoding = response.charset_encoding or "utf-8"

    return b"".join(chunks).decode(encoding, errors="replace")
