from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON, DateTime, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.db.base import Base

class VoteType(str, enum.Enum):
    FUNNY = "funny"
    NOT_FUNNY = "not_funny"

class ReZoKeVoteType(str, enum.Enum):
    UP = "up"
    DOWN = "down"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firebase_uid = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    emoji_avatar = Column(String, default="🐼")
    humor_score = Column(Integer, default=0)
    zoscore = Column(Integer, default=0)
    badge_level = Column(String, server_default='new')
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    jokes_voted = relationship("JokeVote", back_populates="user")
    rezokes = relationship("ReZoKe", back_populates="user")
    rezokes_voted = relationship("ReZoKeVote", back_populates="user")
    
    # Zokers (Followers) System
    followers = relationship(
        "Follow",
        foreign_keys="Follow.followed_id",
        back_populates="followed",
        cascade="all, delete-orphan"
    )
    following = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan"
    )
    
    saved_jokes = relationship("SavedJoke", back_populates="user", cascade="all, delete-orphan")

class Follow(Base):
    __tablename__ = "follows"

    follower_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    followed_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    follower = relationship("User", foreign_keys=[follower_id], back_populates="following")
    followed = relationship("User", foreign_keys=[followed_id], back_populates="followers")

class SavedJoke(Base):
    __tablename__ = "saved_jokes"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    joke_id = Column(UUID(as_uuid=True), ForeignKey("jokes.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="saved_jokes")
    joke = relationship("Joke")

class Joke(Base):
    __tablename__ = "jokes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    hash = Column(String, unique=True, index=True, nullable=False) # specific hash of the joke text
    source = Column(String, nullable=True, default="manual")
    shares_count = Column(Integer, default=0)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True) # Optional for system jokes
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="created_jokes", foreign_keys=[user_id])
    votes = relationship("JokeVote", back_populates="joke", cascade="all, delete-orphan")
    rezokes = relationship("ReZoKe", back_populates="joke", cascade="all, delete-orphan")

class ReZoKe(Base):
    __tablename__ = "rezokes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    joke_id = Column(UUID(as_uuid=True), ForeignKey("jokes.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False) # The user's rewrite of the joke
    vote_score = Column(Integer, default=0, index=True)
    funny_count = Column(Integer, default=0)
    not_funny_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    joke = relationship("Joke", back_populates="rezokes")
    user = relationship("User", back_populates="rezokes")
    votes = relationship("ReZoKeVote", back_populates="rezoke")

class JokeVote(Base):
    __tablename__ = "joke_votes"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    joke_id = Column(UUID(as_uuid=True), ForeignKey("jokes.id"), primary_key=True)
    vote_type = Column(Enum(VoteType), nullable=False)

    user = relationship("User", back_populates="jokes_voted")
    joke = relationship("Joke", back_populates="votes")

class ReZoKeVote(Base):
    __tablename__ = "rezoke_votes"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    rezoke_id = Column(UUID(as_uuid=True), ForeignKey("rezokes.id"), primary_key=True)
    vote_type = Column(Enum(ReZoKeVoteType), nullable=False)

    user = relationship("User", back_populates="rezokes_voted")
    rezoke = relationship("ReZoKe", back_populates="votes")

class JokeView(Base):
    __tablename__ = "joke_views"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    joke_id = Column(UUID(as_uuid=True), ForeignKey("jokes.id"), primary_key=True)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    joke = relationship("Joke")
