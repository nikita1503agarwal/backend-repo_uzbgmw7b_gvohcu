"""
Database Schemas for AniTrack

Each Pydantic model below maps to a MongoDB collection (lowercased class name).
- User -> "user"
- WatchEntry -> "watchentry"
- Rating -> "rating"

These are used for validating input/output and structuring stored documents.
"""
from pydantic import BaseModel, Field
from typing import Optional, List

class User(BaseModel):
    username: str = Field(..., description="Display username")
    email: Optional[str] = Field(None, description="Optional email for account recovery")
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

class WatchEntry(BaseModel):
    user_id: str = Field(..., description="App-level user id or anonymous session id")
    mal_id: int = Field(..., description="MyAnimeList ID from Jikan")
    title: str = Field(..., description="Anime title snapshot")
    image_url: Optional[str] = None
    status: str = Field("completed", description="completed, watching, dropped, on_hold, planned")
    episodes_watched: int = Field(0, ge=0)
    total_episodes: Optional[int] = Field(None, ge=0)
    score: Optional[float] = Field(None, ge=0, le=10)
    genres: List[str] = Field(default_factory=list)

class Rating(BaseModel):
    user_id: str
    mal_id: int
    score: float = Field(..., ge=0, le=10)
    review: Optional[str] = None
