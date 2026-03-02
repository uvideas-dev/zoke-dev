from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.db.session import get_db
from app.models.all_models import Joke, JokeVote, VoteType
from app.schemas import schemas as s
from typing import List

router = APIRouter()

@router.get("/trending", response_model=List[s.Joke])
async def get_trending_jokes(
    db: AsyncSession = Depends(get_db)
):
    """
    Get Top 10 funniest jokes based on 'funny' vote counts.
    """
    # Create a subquery to count funny votes per joke
    funny_votes = (
        select(JokeVote.joke_id, func.count().label("funny_count"))
        .where(JokeVote.vote_type == VoteType.FUNNY)
        .group_by(JokeVote.joke_id)
        .subquery()
    )
    
    from sqlalchemy.orm import selectinload
    # Join with Joke table and order by funny_count
    query = (
        select(Joke)
        .join(funny_votes, Joke.id == funny_votes.c.joke_id)
        .options(selectinload(Joke.user))
        .order_by(desc(funny_votes.c.funny_count))
        .limit(10)
    )
    
    result = await db.execute(query)
    jokes = list(result.scalars().all())
    from app.api.v1.endpoints.jokes import enrich_joke_stats
    await enrich_joke_stats(db, jokes)
    return jokes

@router.get("/categories")
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    Get a list of unique categories.
    """
    query = select(Joke.category).distinct().where(Joke.category != None)
    result = await db.execute(query)
    categories = result.scalars().all()
    return categories
