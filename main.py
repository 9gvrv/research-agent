import asyncio
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

dotenv_path = Path("./.env")
load_dotenv(dotenv_path=dotenv_path)

searxng_search_engine_url = os.getenv("SEARXNG_URL")
print(repr(searxng_search_engine_url))


async def search_searxng(query: str):
    params = {"q": query, "format": "json", "language": "en"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(f"{searxng_search_engine_url}", params=params)
        response.raise_for_status()
        data = response.json()
    return data.get("results", [])


async def main():
    print("Hello from research-agent!")

    while True:
        user_input = input("Query: ")
        if user_input.lower() == "/exit":
            break
        print(f"User input: {user_input}\n$", end="")
        results = await search_searxng(user_input)
        for r in results[:10]:
            print(r["title"], "→", r["url"])


asyncio.run(main())
