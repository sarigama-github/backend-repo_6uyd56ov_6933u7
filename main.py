import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SOURCE_URL = "https://www.febryardiansyah.my.id/"


def scrape_portfolio(url: str):
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Unable to fetch source site: {e}")

    soup = BeautifulSoup(res.text, "html.parser")

    # Title and description
    title = soup.title.string.strip() if soup.title else ""
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    description = meta_desc_tag.get("content", "").strip() if meta_desc_tag else ""

    # Hero text (common selectors)
    h1 = soup.find("h1")
    hero = h1.get_text(strip=True) if h1 else title

    # Collect sections by common ids/classes
    sections = []
    for sec in soup.find_all(["section", "div"], recursive=True):
        sec_id = sec.get("id") or ""
        cls = " ".join(sec.get("class", []))
        if any(k in (sec_id + " " + cls).lower() for k in ["about", "skills", "project", "work", "experience", "contact", "service", "portfolio"]):
            text = " ".join(t.strip() for t in sec.stripped_strings)
            if len(text) > 60:  # avoid tiny blocks
                sections.append({
                    "id": sec_id,
                    "class": cls,
                    "text": text[:1200]
                })

    # Links to projects (anchors with target or github/live)
    projects = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        label = a.get_text(strip=True)
        if any(k in href.lower() for k in ["github", "project", "work", "case", "dribbble", "behance", "vercel", "netlify"]):
            projects.append({"label": label, "url": href})
    # deduplicate
    seen = set()
    unique_projects = []
    for p in projects:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique_projects.append(p)

    # Social links
    socials = []
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        label = a.get_text(strip=True)
        for key in ["github", "linkedin", "twitter", "x.com", "instagram", "youtube", "medium", "dev.to"]:
            if key in href:
                socials.append({"platform": key.split(".")[0].replace("x", "twitter"), "url": a["href"], "label": label})
                break
    # unique socials by platform
    s_seen = set()
    unique_socials = []
    for s in socials:
        if s["platform"] not in s_seen:
            s_seen.add(s["platform"])
            unique_socials.append(s)

    return {
        "title": title,
        "description": description,
        "hero": hero,
        "sections": sections[:6],
        "projects": unique_projects[:12],
        "socials": unique_socials[:8],
        "source": url,
    }


@app.get("/")
def read_root():
    return {"message": "Portfolio API running"}


@app.get("/api/portfolio")
def get_portfolio():
    return scrape_portfolio(SOURCE_URL)


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception:
        response["database"] = "❌ Database module not found"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
