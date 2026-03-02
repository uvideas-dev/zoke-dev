from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum

class VoteType(str, Enum):
    FUNNY = "funny"
    NOT_FUNNY = "not_funny"

class ReZoKeVoteType(str, Enum):
    UP = "up"
    DOWN = "down"

# User Schemas
class UserBase(BaseModel):
    firebase_uid: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    bio: Optional[str] = None
    emoji_avatar: Optional[str] = None

class User(UserBase):
    id: UUID
    username: Optional[str]
    bio: Optional[str]
    emoji_avatar: str
    humor_score: int
    zoscore: int = 0
    badge_level: Optional[str] = None
    title: str = "ZoKer"
    zokers_count: int = 0
    zoking_count: int = 0
    is_following: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

# Joke Schemas
class JokeUserBase(BaseModel):
    id: UUID
    username: Optional[str] = "ZoKer"
    emoji_avatar: str

    class Config:
        from_attributes = True

class JokeBase(BaseModel):
    text: str
    category: Optional[str] = None
    source: Optional[str] = "jokeapi"

class JokeCreate(JokeBase):
    hash: Optional[str] = None

class Joke(JokeBase):
    id: UUID
    hash: Optional[str] = None
    user_id: Optional[UUID] = None
    user: Optional[JokeUserBase] = None
    created_at: datetime
    is_following_user: bool = False
    funny_count: int = 0
    not_funny_count: int = 0
    rezokes_count: int = 0
    shares_count: int = 0
    user_vote: Optional[VoteType] = None

    class Config:
        from_attributes = True

# ReZoKe Schemas
class ReZoKeBase(BaseModel):
    text: str

class ReZoKeCreate(ReZoKeBase):
    joke_id: UUID

class ReZoKe(ReZoKeBase):
    id: UUID
    joke_id: UUID
    user_id: UUID
    joke: Optional[Joke] = None
    user: Optional[JokeUserBase] = None
    vote_score: int = 0
    funny_count: int = 0
    not_funny_count: int = 0
    shares_count: int = 0
    user_vote: Optional[ReZoKeVoteType] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Vote Schemas
class JokeVoteCreate(BaseModel):
    joke_id: UUID
    vote_type: VoteType

class ReZoKeVoteCreate(BaseModel):
    rezoke_id: UUID
    vote_type: ReZoKeVoteType
