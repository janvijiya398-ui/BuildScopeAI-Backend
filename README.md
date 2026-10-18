
# BuildScope AI — Backend

FastAPI backend for researching project ideas, collecting competitor website evidence, and generating a preliminary Buildability Passport.

## Features

- FastAPI REST API
- TinyFish-powered web search
- Competitor website fetching
- Preliminary competitor feature comparison
- Buildability Passport generation
- Evidence links, suggested MVP features, and risk identification

## Tech Stack

- Python
- FastAPI
- Uvicorn
- Requests
- Python-dotenv
- TinyFish Search and Fetch APIs

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Backend welcome message |
| GET | `/health` | Health check |
| POST | `/research` | Search for information |
| POST | `/fetch` | Fetch website content |
| POST | `/competitor` | Fetch a competitor website report |
| POST | `/idea-research` | Generate competitor research and a Buildability Passport |

## Setup

1. Install Python.
2. Clone this repository.
3. Create and activate a virtual environment.
4. Install dependencies:

   `python -m pip install -r requirements.txt`

5. Create a `.env` file in the project root:

   `TINYFISH_API_KEY=your_api_key_here`

6. Start the server:

   `python -m uvicorn main:app`

7. Open the interactive API documentation at:

   `http://127.0.0.1:8000/docs`

## Example Request

POST `/idea-research`

```json
{
  "idea": "An AI platform for discovering college hackathons, internships, and campus events"
}
```

## Research Limitations

Competitor feature signals are based on words found in fetched website content. They are preliminary indicators, not independently verified feature claims. Market demand and feasibility require further validation.

## Security

Never commit `.env`, API keys, or the `.venv` directory.
