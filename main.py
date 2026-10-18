
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from database import Project, Requirement, get_db, init_db

load_dotenv()

app = FastAPI(title="BuildScope AI")

init_db()
class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=300)


@app.get("/")
def home():
    return {
        "message": "BuildScope AI backend is running!"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@app.post("/research")
def research(request: ResearchRequest):
    api_key = os.getenv("TINYFISH_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="TinyFish API key is not configured."
        )

    try:
        response = requests.get(
            "https://api.search.tinyfish.ai",
            params={"query": request.query},
            headers={"X-API-Key": api_key},
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="TinyFish research request failed."
        )
    
class FetchRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=5)


@app.post("/fetch")
def fetch_pages(request: FetchRequest):
    api_key = os.getenv("TINYFISH_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="TinyFish API key is not configured."
        )

    try:
        response = requests.post(
            "https://api.fetch.tinyfish.ai",
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            },
            json={"urls": request.urls},
            timeout=60
        )

        response.raise_for_status()
        return response.json()

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="TinyFish page-fetch request failed."
        )


class CompetitorRequest(BaseModel):
    url: str = Field(min_length=8, max_length=500)


@app.post("/competitor")
def competitor_report(request: CompetitorRequest):
    api_key = os.getenv("TINYFISH_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="TinyFish API key is not configured."
        )

    if not request.url.startswith(("https://", "http://")):
        raise HTTPException(
            status_code=422,
            detail="Please provide a valid HTTP or HTTPS URL."
        )

    try:
        response = requests.post(
            "https://api.fetch.tinyfish.ai",
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            },
            json={"urls": [request.url]},
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])

        if not results:
            raise HTTPException(
                status_code=502,
                detail="No page content was returned."
            )

        page = results[0]

        return {
            "competitor": {
                "name": page.get("title", "Unknown"),
                "url": page.get("final_url") or page.get("url"),
                "description": page.get("description"),
                "claimed_features": (page.get("text") or "")[:4000],
                "evidence_source": page.get("final_url") or page.get("url"),
                "analysis_status": "Fetched; claims not independently verified"
            }
        }

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="TinyFish could not fetch the competitor page."
        )

class IdeaResearchRequest(BaseModel):
    idea: str = Field(min_length=10, max_length=1000)




@app.post("/idea-research")
def idea_research(request: IdeaResearchRequest):
    api_key = os.getenv("TINYFISH_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="TinyFish API key is not configured."
        )

    try:
        # Step 1: Search for competitors
        search_response = requests.get(
            "https://api.search.tinyfish.ai",
            params={
                "query": (
                    "existing products platforms competitors for: "
                    + request.idea
                )
            },
            headers={"X-API-Key": api_key},
            timeout=30
        )
        search_response.raise_for_status()

        search_data = search_response.json()
        search_results = search_data.get("results", [])[:10]

        # Step 2: Select up to 3 websites to investigate
        urls = [
            item.get("url")
            for item in search_results
            if item.get("url", "").startswith("https://")
        ][:3]

        # Step 3: Fetch those websites
        fetched_pages = []

        if urls:
            fetch_response = requests.post(
                "https://api.fetch.tinyfish.ai",
                headers={
                    "X-API-Key": api_key,
                    "Content-Type": "application/json"
                },
                json={"urls": urls},
                timeout=60
            )
            fetch_response.raise_for_status()

            fetch_data = fetch_response.json()
            fetched_pages = fetch_data.get("results", [])

        # Step 4: Prepare competitor information
        competitors = [
            {
                "name": page.get("title") or "Unknown",
                "url": page.get("final_url") or page.get("url"),
                "description": page.get("description"),
                "page_content": (page.get("text") or "")[:1500],
                "evidence_source": (
                    page.get("final_url") or page.get("url")
                ),
                "analysis_status": (
                    "Website fetched; claims not independently verified"
                )
            }
            for page in fetched_pages
        ]

        # Step 5: Compare features mentioned on competitor pages
        feature_comparison = compare_competitors(competitors)

        # Step 6: Generate the Buildability Passport
        passport = generate_buildability_passport(
            request.idea,
            competitors,
            feature_comparison
        )

        # Step 7: Return the complete report
        return {
            "idea": request.idea,
            "search_results_count": len(search_results),
            "feature_comparison": feature_comparison,
            "competitors": competitors,
            "additional_leads": [
                {
                    "name": item.get("title"),
                    "url": item.get("url"),
                    "description": item.get("snippet")
                }
                for item in search_results
                if item.get("url") not in urls
            ],
            "buildability_passport": passport,
            "next_step": (
                "Validate customer demand and manually verify "
                "competitor claims before making a feasibility decision."
            )
        }

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="TinyFish idea research failed."
        )

    
def compare_competitors(competitors):
    comparison = []

    for competitor in competitors:
        content = (
            competitor.get("page_content") or ""
        ).lower()

        features = {
            "hackathon_discovery": any(
                word in content
                for word in ["hackathon", "hackathons"]
            ),
            "internship_opportunities": any(
                word in content
                for word in ["internship", "internships", "fellowship"]
            ),
            "student_community": any(
                word in content
                for word in ["student", "students", "community"]
            ),
            "event_discovery": any(
                word in content
                for word in ["events", "event", "upcoming"]
            )
        }

        comparison.append({
            "competitor_name": competitor.get("name"),
            "source": competitor.get("evidence_source"),
            "features_mentioned_on_page": features
        })

    return comparison


def generate_buildability_passport(idea, competitors, feature_comparison):
    return {
        "idea": idea,
        "problem_validation": {
            "status": "Needs validation",
            "finding": (
                "Competitor research can identify existing solutions, "
                "but it does not yet prove customer demand."
            )
        },
        "competitive_landscape": {
            "competitors_found": len(competitors),
            "feature_comparison": feature_comparison
        },
        "differentiation_opportunities": [
            {
                "opportunity": (
                    "Explore combining hackathons, internships, "
                    "and campus events in one student-focused platform."
                ),
                "status": "Hypothesis to validate"
            }
        ],
        "suggested_mvp": [
            "Search and browse opportunities",
            "Filter by opportunity type and deadline",
            "Show original source links",
            "Save opportunities"
        ],
        "key_risks": [
            "Opportunity listings may become outdated",
            "Some sources may not permit automated collection",
            "Competitor feature signals need manual verification",
            "Student demand has not yet been validated"
        ],
        "evidence": [
            {
                "name": competitor.get("name"),
                "url": competitor.get("evidence_source"),
                "status": "Website fetched; claims not independently verified"
            }
            for competitor in competitors
        ],
        "overall_status": "Preliminary research; not yet validated"
    }
# ---------------- PROJECT DATABASE APIs ----------------

class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    idea: str = Field(min_length=10, max_length=2000)
    target_users: str = Field(min_length=2, max_length=300)
    problem_statement: str = Field(min_length=10, max_length=2000)
    expected_outcome: str = Field(min_length=5, max_length=2000)


class ProjectResponse(ProjectCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RequirementCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=5, max_length=2000)
    requirement_type: str = Field(
        default="functional",
        pattern="^(functional|non-functional)$"
    )
    priority: str = Field(
        default="medium",
        pattern="^(low|medium|high)$"
    )


class RequirementResponse(RequirementCreate):
    id: int
    project_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@app.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db)
):
    project = Project(**project_data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/projects", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.id.desc()).all()


@app.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    return project


@app.post(
    "/projects/{project_id}/requirements",
    response_model=RequirementResponse,
    status_code=201
)
def create_requirement(
    project_id: int,
    requirement_data: RequirementCreate,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    requirement = Requirement(
        project_id=project_id,
        **requirement_data.model_dump()
    )

    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


@app.get(
    "/projects/{project_id}/requirements",
    response_model=list[RequirementResponse]
)
def list_requirements(
    project_id: int,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    return (
        db.query(Requirement)
        .filter(Requirement.project_id == project_id)
        .order_by(Requirement.id.asc())
        .all()
    )
