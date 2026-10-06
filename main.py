import asyncio
import os
from email.policy import default
from pathlib import Path

import httpx
from dotenv import load_dotenv
from trafilatura import extract, fetch_url

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


async def fetch_page(url: str):
    downloaded = fetch_url(url)

    text = extract(downloaded, output_format="markdown", with_metadata=True)

    return text


async def main():
    print("Hello from research-agent!")

    while True:
        user_input = input("Query: ")
        if user_input[0].lower() == "/":
            match user_input:
                case "/exit":
                    break
                case _:
                    print("Help menu")
        else:
            print(f"User input: {user_input}\n$", end="")
            results = await search_searxng(user_input)
            urls = []
            for r in results[:10]:
                print(r["title"], "→", r["url"])
                urls.append(r["url"])

            data = []
            print("Searching web....")
            for url in urls:
                res = await fetch_page(url)
                data.append(res)

            print(f"========== Result ==========\n{data}")


asyncio.run(main())
