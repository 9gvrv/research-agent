import asyncio
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from groq import Groq
from trafilatura import extract, fetch_url

from commands.clear_terminal import clear_terminal
from web_processor import process_urls

dotenv_path = Path("./.env")
load_dotenv(dotenv_path=dotenv_path)
gemini_api_key = os.getenv("GEMINI_API_KEY2")
searxng_search_engine_url = os.getenv("SEARXNG_URL")
print(repr(searxng_search_engine_url))
client = genai.Client(api_key=gemini_api_key)


def fake_research_router(query: str, return_response: int) -> str:
    responses = {
        1: {
            "action": "answer",
            "reason": "The query can be answered reliably without current external information.",
            "answer": "A Python decorator modifies or extends the behavior of another function.",
            "queries": [],
            "clarification": "",
        },
        2: {
            "action": "research",
            "reason": "The query depends on current information, so web research would meaningfully improve the answer.",
            "answer": "",
            "queries": [
                "latest React release changes 2026",
                "React developer discussion latest release",
            ],
            "clarification": "",
        },
        3: {
            "action": "clarify",
            "reason": "The query is too ambiguous to determine the user's intended question.",
            "answer": "",
            "queries": [],
            "clarification": "Could you clarify what you would like to know?",
        },
        4: {
            "action": "research",
            "reason": "The query concerns a specific current topic where external sources would improve the answer.",
            "answer": "",
            "queries": [
                "Claude Code latest developer discussion 2026",
                "Claude Code official documentation",
            ],
            "clarification": "",
        },
    }

    if return_response not in responses:
        raise ValueError("return_response must be 1, 2, 3, or 4")

    return json.dumps(responses[return_response])


async def research_router(query: str):
    print("pondering...")
    with open("./prompts/research_router.md", "r", encoding="utf-8") as f:
        system_prompt_content = f.read()

    print("starting research_router interaction api")
    interaction = await client.aio.interactions.create(
        model="gemini-2.5-flash", system_instruction=system_prompt_content, input=query
    )
    print("research_router interaction api completed")

    return interaction.output_text


async def research_router_openai(query: str):
    print("pondering.....")
    with open("./prompts/research_router.md", "r", encoding="utf-8") as f:
        system_prompt_content = f.read()

    client = Groq()

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": f"{system_prompt_content}"},
            {"role": "user", "content": f"{query}"},
        ],
    )

    return response.choices[0].message.content


async def search_searxng(query: str, limit: int = 3):
    params = {"q": query, "format": "json", "language": "en"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(f"{searxng_search_engine_url}", params=params)
        response.raise_for_status()
        data = response.json()

    return [
        result["url"] for result in data.get("results", [])[:limit] if result.get("url")
    ]


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
            research_router_response_string = await research_router_openai(user_input)
            # research_router_response_string = fake_research_router(
            #     "latest news", return_response=2
            # )
            research_router_response = json.loads(research_router_response_string)

            match research_router_response["action"]:
                case "answer":
                    print(f"{research_router_response['answer']}")

                case "research":
                    urls = []
                    for query in research_router_response["queries"]:
                        o = await search_searxng(query)
                        urls.extend(o)

                    print(f"Researching...\n {urls}")
                    data = []
                    print("Searching web....")
                    documents = await process_urls(urls)
                    for document in documents:
                        print(document.to_llm())
                        print()


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
