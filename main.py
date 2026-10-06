import asyncio
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from trafilatura import extract, fetch_url

from commands.clear_terminal import clear_terminal

dotenv_path = Path("./.env")
load_dotenv(dotenv_path=dotenv_path)
gemini_api_key = os.getenv("GEMINI_API_KEY")
searxng_search_engine_url = os.getenv("SEARXNG_URL")
print(repr(searxng_search_engine_url))
client = genai.Client(api_key=gemini_api_key)


async def research_router(query: str):
    print("pondering...")
    with open("./prompts/research_router.md", "r", encoding="utf-8") as f:
        system_prompt_content = f.read()

    interaction = await client.aio.interactions.create(
        model="gemini-2.5-flash", system_instruction=system_prompt_content, input=query
    )

    return interaction.output_text


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
                case "/clear":
                    clear_terminal()
                case _:
                    print("Help menu")
        else:
            print(f"User input: {user_input}\n$", end="")
            print(await research_router(user_input))


#             results = await search_searxng(user_input)
#             urls = []
#             for r in results[:10]:
#                 print(r["title"], "→", r["url"])
#                 urls.append(r["url"])
#
#             data = []
#             print("Searching web....")
#             for url in urls:
#                 res = await fetch_page(url)
#                 data.append(res)
#
#             print(f"========== Result ==========\n{data}")


asyncio.run(main())
