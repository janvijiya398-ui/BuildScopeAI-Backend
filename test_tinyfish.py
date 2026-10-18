
import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("TINYFISH_API_KEY")

if not api_key:
    print("ERROR: API key not found. Check your .env file.")
else:
    try:
        response = requests.get(
            "https://api.search.tinyfish.ai",
            params={"query": "official FastAPI documentation"},
            headers={"X-API-Key": api_key},
            timeout=20
        )

        response.raise_for_status()
        data = response.json()

        print("SUCCESS! TinyFish is connected!")
        print("\nSearch results:\n")

        for result in data.get("results", [])[:3]:
            print("Title:", result.get("title", "No title"))
            print("URL:", result.get("url", "No URL"))
            print("Snippet:", result.get("snippet", "No snippet"))
            print("-" * 40)

    except requests.RequestException as error:
        print("Request failed:", error)
        print("Check your internet connection and API key.")
