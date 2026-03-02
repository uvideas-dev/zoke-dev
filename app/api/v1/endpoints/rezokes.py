from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.session import get_db
from app.core.security import get_current_user, get_optional_user
from app.models.all_models import User, ReZoKe, ReZoKeVote, VoteType
from app.core.redis_client import get_redis
import json
from app.schemas.schemas import ReZoKeCreate, ReZoKeVoteCreate, ReZoKe as ReZoKeSchema
from typing import List
import uuid

router = APIRouter()

@router.post("", response_model=dict)
async def create_rezoke(
    rezoke_in: ReZoKeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_rezoke = ReZoKe(
        user_id=current_user.id,
        joke_id=rezoke_in.joke_id,
        text=rezoke_in.text
    )
    db.add(new_rezoke)
    await db.commit()
    return {"status": "success", "id": str(new_rezoke.id)}

@router.get("/{joke_id}", response_model=List[ReZoKeSchema])
async def get_rezokes_for_joke(
    joke_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user),
    redis = Depends(get_redis)
):
    """
    Fetch top-voted ReZoKes with pagination and Redis caching for the first page.
    """
    redis_key = f"rezokes:{joke_id}:{page}"
    
    # 1. Try Redis for page 1
    if page == 1:
        cached_rezokes = await redis.get(redis_key)
        if cached_rezokes:
            try:
                # We store as ID list for freshness or full objects for speed?
                # User asked to cache the actual ReZoKes I assume
                return json.loads(cached_rezokes)
            except:
                pass

    # 2. Fetch from DB
    from sqlalchemy.orm import selectinload
    query = (
        select(ReZoKe)
        .where(ReZoKe.joke_id == joke_id)
        .options(selectinload(ReZoKe.user))
        .order_by(desc(ReZoKe.funny_count), desc(ReZoKe.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    rezokes = list(result.scalars().all())
    
    # 3. Enrich with user votes
    if current_user and rezokes:
        rz_ids = [r.id for r in rezokes]
        uv_q = select(ReZoKeVote.rezoke_id, ReZoKeVote.vote_type).where(
            ReZoKeVote.rezoke_id.in_(rz_ids), ReZoKeVote.user_id == current_user.id
        )
        uv_res = await db.execute(uv_q)
        uv_map = {r[0]: r[1] for r in uv_res.all()}
        for r in rezokes:
            r.user_vote = uv_map.get(r.id)

    # 4. Cache page 1 results
    if page == 1 and rezokes:
        # Convert to serializable format (simple for now)
        from fastapi.encoders import jsonable_encoder
        serializable = jsonable_encoder(rezokes)
        await redis.set(redis_key, json.dumps(serializable), ex=300) # 5 minutes

    return rezokes

@router.post("/vote")
async def vote_rezoke(
    vote: ReZoKeVoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.services.reputation_service import update_user_zoscore
    
    rezoke = await db.get(ReZoKe, vote.rezoke_id)
    if not rezoke:
        raise HTTPException(status_code=404, detail="ReZoKe not found")

    # Rule: Users cannot vote on their own content
    is_own_content = rezoke.user_id == current_user.id

    query = select(ReZoKeVote).where(
        ReZoKeVote.user_id == current_user.id,
        ReZoKeVote.rezoke_id == vote.rezoke_id
    )
    result = await db.execute(query)
    existing_vote = result.scalars().first()

    f_delta = 0
    nf_delta = 0
    score_change = 0
    
    if existing_vote:
        if existing_vote.vote_type == vote.vote_type:
            # Toggle OFF
            if existing_vote.vote_type == "up": 
                f_delta = -1
                score_change = -1
            else: 
                nf_delta = -1
                score_change = 1
            await db.delete(existing_vote)
        else:
            # Change vote
            if vote.vote_type == "up":
                f_delta = 1
                nf_delta = -1
                score_change = 2 # Down to Up: -(-1) + 1 = 2
            else:
                f_delta = -1
                nf_delta = 1
                score_change = -2 # Up to Down: -1 + (-1) = -2
            existing_vote.vote_type = vote.vote_type
    else:
        # New vote
        if vote.vote_type == "up": 
            f_delta = 1
            score_change = 1
        else: 
            nf_delta = 1
            score_change = -1
            
        new_vote = ReZoKeVote(
            user_id=current_user.id,
            rezoke_id=vote.rezoke_id,
            vote_type=vote.vote_type
        )
        db.add(new_vote)
    
    rezoke.funny_count = max(0, rezoke.funny_count + f_delta)
    rezoke.not_funny_count = max(0, rezoke.not_funny_count + nf_delta)
    rezoke.vote_score = rezoke.funny_count - rezoke.not_funny_count
    
    # Update ZoScore only if not voting on own content and score should change
    updated_creator = None
    if not is_own_content and rezoke.user_id and score_change != 0:
        updated_creator = await update_user_zoscore(db, rezoke.user_id, score_change)

    await db.commit()
    
    return {
        "status": "success", 
        "funny_count": rezoke.funny_count, 
        "not_funny_count": rezoke.not_funny_count,
        "zoscore": updated_creator.zoscore if updated_creator else None,
        "badge_level": updated_creator.badge_level if updated_creator else None
    }

@router.post("/share/{rezoke_id}")
async def track_share(
    rezoke_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Increment share count for a ReZoKe.
    """
    rezoke = await db.get(ReZoKe, rezoke_id)
    if not rezoke:
        raise HTTPException(status_code=404, detail="ReZoKe not found")
    
    rezoke.shares_count += 1
    await db.commit()
    return {"status": "success", "shares_count": rezoke.shares_count}
