import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
import requests

from database import db, create_document, get_documents
from schemas import User, WatchEntry, Rating

app = FastAPI(title="AniTrack API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JIKAN_BASE = "https://api.jikan.moe/v4"

class CreateWatchEntry(BaseModel):
    user_id: str
    mal_id: int
    title: str
    image_url: Optional[str] = None
    status: str = "completed"
    episodes_watched: int = 0
    total_episodes: Optional[int] = None
    score: Optional[float] = None
    genres: Optional[List[str]] = None

class CreateRating(BaseModel):
    user_id: str
    mal_id: int
    score: float
    review: Optional[str] = None

@app.get("/")
def root():
    return {"message": "AniTrack Backend is running"}

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
        if db is not None:
            response["database"] = "✅ Available"
            response["database_name"] = getattr(db, 'name', None)
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# --------------------------
# Jikan proxy endpoints
# --------------------------

@app.get("/api/search")
def search_anime(q: str = Query(..., min_length=2), page: int = 1):
    try:
        r = requests.get(f"{JIKAN_BASE}/anime", params={"q": q, "page": page, "order_by": "popularity"}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Jikan error: {str(e)}")

@app.get("/api/anime/{mal_id}")
def get_anime(mal_id: int):
    try:
        r = requests.get(f"{JIKAN_BASE}/anime/{mal_id}", timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Jikan error: {str(e)}")

@app.get("/api/suggestions")
def get_suggestions(page: int = 1):
    """Use Jikan top anime as suggestions."""
    try:
        r = requests.get(f"{JIKAN_BASE}/top/anime", params={"page": page}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Jikan error: {str(e)}")

# --------------------------
# Watch history & ratings (MongoDB)
# --------------------------

@app.post("/api/watch")
def add_watch(entry: CreateWatchEntry):
    try:
        doc_id = create_document("watchentry", WatchEntry(**entry.model_dump()))
        return {"id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/watch/{user_id}")
def get_watch_history(user_id: str, limit: int = 50):
    try:
        items = get_documents("watchentry", {"user_id": user_id}, limit)
        # Convert ObjectId and datetime to strings
        def clean(d: Any):
            d = dict(d)
            if "_id" in d:
                d["_id"] = str(d["_id"])
            for k, v in list(d.items()):
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
            return d
        return [clean(x) for x in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rate")
def rate_anime(payload: CreateRating):
    try:
        doc_id = create_document("rating", Rating(**payload.model_dump()))
        return {"id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rate/{user_id}")
def get_user_ratings(user_id: str, limit: int = 100):
    try:
        items = get_documents("rating", {"user_id": user_id}, limit)
        def clean(d: Any):
            d = dict(d)
            if "_id" in d:
                d["_id"] = str(d["_id"])
            for k, v in list(d.items()):
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
            return d
        return [clean(x) for x in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
