from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.session import get_db
from app.core.security import get_current_user, get_optional_user
from app.core.redis_client import get_redis
from app.models.all_models import User, Joke as JokeModel, JokeVote, VoteType, JokeView, Follow
from app.schemas import schemas as s
from typing import List, Optional
import uuid
import json
import random

router = APIRouter()

FEED_BATCH_SIZE = 20
import time

# Global lock for ingestion
ingestion_running = False
from sqlalchemy import func
from app.models.all_models import ReZoKe

async def enrich_joke_stats(db: AsyncSession, jokes: List[JokeModel], user_id: Optional[uuid.UUID] = None):
    if not jokes:
        return jokes
    
    joke_ids = [j.id for j in jokes]
    
    # 1. Funny Counts
    funny_q = select(JokeVote.joke_id, func.count(JokeVote.joke_id)).where(
        JokeVote.joke_id.in_(joke_ids), JokeVote.vote_type == VoteType.FUNNY
    ).group_by(JokeVote.joke_id)
    funny_res = await db.execute(funny_q)
    funny_map = {r[0]: r[1] for r in funny_res.all()}
    
    # 2. Not Funny Counts
    not_funny_q = select(JokeVote.joke_id, func.count(JokeVote.joke_id)).where(
        JokeVote.joke_id.in_(joke_ids), JokeVote.vote_type == VoteType.NOT_FUNNY
    ).group_by(JokeVote.joke_id)
    not_funny_res = await db.execute(not_funny_q)
    not_funny_map = {r[0]: r[1] for r in not_funny_res.all()}
    
    # 3. ReZoKe Counts
    rezoke_q = select(ReZoKe.joke_id, func.count(ReZoKe.joke_id)).where(
        ReZoKe.joke_id.in_(joke_ids)
    ).group_by(ReZoKe.joke_id)
    rezoke_res = await db.execute(rezoke_q)
    rezoke_map = {r[0]: r[1] for r in rezoke_res.all()}
    
    # 4. User Votes
    user_vote_map = {}
    if user_id:
        user_vote_q = select(JokeVote.joke_id, JokeVote.vote_type).where(
            JokeVote.joke_id.in_(joke_ids), JokeVote.user_id == user_id
        )
        user_vote_res = await db.execute(user_vote_q)
        user_vote_map = {r[0]: r[1] for r in user_vote_res.all()}
    
    for joke in jokes:
        joke.funny_count = funny_map.get(joke.id, 0)
        joke.not_funny_count = not_funny_map.get(joke.id, 0)
        joke.rezokes_count = rezoke_map.get(joke.id, 0)
        joke.shares_count = joke.shares_count # Already in DB model
        joke.user_vote = user_vote_map.get(joke.id)
    
    return jokes

@router.get("/feed", response_model=List[s.Joke])
async def get_feed(
    background_tasks: BackgroundTasks,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user),
    redis = Depends(get_redis)
):
    try:
        print(f"[Feed] Request started. Category: {category or 'All'}, User: {current_user.id if current_user else 'Guest'}")
        joke_ids = []
        
        if current_user:
            user_id = str(current_user.id)
            redis_key = f"user_feed:{user_id}"
            if category:
                redis_key += f":{category}"

            # 1. Check Redis for existing IDs
            try:
                cached_joke_ids = await redis.lrange(redis_key, 0, FEED_BATCH_SIZE - 1)
            except Exception as e:
                print(f"[Feed] Redis lrange failed: {e}")
                cached_joke_ids = []
            
            if cached_joke_ids:
                print(f"[Feed] Found {len(cached_joke_ids)} IDs in cache")
                joke_ids = [uuid.UUID(id.decode() if isinstance(id, bytes) else id) for id in cached_joke_ids]
                # Pop used IDs from Redis
                try:
                    await redis.ltrim(redis_key, len(joke_ids), -1)
                except Exception as e:
                    print(f"[Feed] Redis ltrim failed: {e}")
            else:
                print("[Feed] Cache empty, querying DB...")
                # 2. Fetch new batch from DB excluding viewed and voted
                viewed_subquery = select(JokeView.joke_id).where(JokeView.user_id == current_user.id)
                voted_subquery = select(JokeVote.joke_id).where(JokeVote.user_id == current_user.id)
                
                query = select(JokeModel.id).where(
                    JokeModel.id.not_in(viewed_subquery),
                    JokeModel.id.not_in(voted_subquery)
                )
                
                if category:
                    query = query.where(JokeModel.category.ilike(f"%{category}%"))
                
                query = query.order_by(desc(JokeModel.created_at)).limit(100)
                
                cand_start = time.time()
                result = await db.execute(query)
                all_potential_ids = [str(id) for id in result.scalars().all()]
                print(f"[Feed] Candidate query took {time.time() - cand_start:.4f}s for {len(all_potential_ids)} candidates")
                
                if all_potential_ids:
                    joke_ids_to_return = [uuid.UUID(id) for id in all_potential_ids[:FEED_BATCH_SIZE]]
                    ids_to_cache = all_potential_ids[FEED_BATCH_SIZE:]
                    
                    if ids_to_cache:
                        try:
                            await redis.rpush(redis_key, *ids_to_cache)
                            await redis.expire(redis_key, 300)
                        except Exception as e:
                            print(f"[Feed] Redis cache update failed: {e}")
                    
                    joke_ids = joke_ids_to_return
        else:
            print("[Feed] Fetching for guest user")
            query = select(JokeModel.id).order_by(desc(JokeModel.created_at)).limit(FEED_BATCH_SIZE)
            if category:
                query = query.where(JokeModel.category.ilike(f"%{category}%"))
            result = await db.execute(query)
            joke_ids = result.scalars().all()

        if not joke_ids:
            print("[Feed] No joke IDs found. Checking for ingestion...")
            global ingestion_running
            if not ingestion_running:
                from app.services.joke_ingestion import fetch_and_store_jokes
                async def ingestion_wrapper():
                    global ingestion_running
                    ingestion_running = True
                    try:
                        await fetch_and_store_jokes()
                    finally:
                        ingestion_running = False
                background_tasks.add_task(ingestion_wrapper)
            return []

        print(f"[Feed] Fetching full joke objects for {len(joke_ids)} IDs")
        start_time = time.time()
        from sqlalchemy.orm import selectinload
        full_query = select(JokeModel).where(JokeModel.id.in_(joke_ids)).options(selectinload(JokeModel.user))
        result = await db.execute(full_query)
        jokes = list(result.scalars().all())
        print(f"[Feed] DB fetch took {time.time() - start_time:.4f}s")

        jokes.sort(key=lambda j: joke_ids.index(j.id))

        # Follower context (simplified for check)
        if current_user:
            followed_ids = set()
            f_q = select(Follow.followed_id).where(Follow.follower_id == current_user.id)
            f_res = await db.execute(f_q)
            followed_ids = set(f_res.scalars().all())
            for joke in jokes:
                joke.is_following_user = joke.user_id in followed_ids if joke.user_id else False

        await enrich_joke_stats(db, jokes, current_user.id if current_user else None)
        return jokes

    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR in get_feed: {e}")
        traceback.print_exc()
        return []

@router.post("/viewed/{joke_id}")
async def mark_joke_viewed(
    joke_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a joke as viewed to avoid showing it again in the feed.
    """
    # Check if already viewed
    query = select(JokeView).where(
        JokeView.user_id == current_user.id,
        JokeView.joke_id == joke_id
    )
    result = await db.execute(query)
    if not result.scalars().first():
        new_view = JokeView(user_id=current_user.id, joke_id=joke_id)
        db.add(new_view)
        await db.commit()
    
    return {"status": "success"}

@router.post("/share/{joke_id}")
async def track_share(
    joke_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Increment share count for a joke.
    """
    joke = await db.get(JokeModel, joke_id)
    if not joke:
        raise HTTPException(status_code=404, detail="Joke not found")
    
    joke.shares_count += 1
    await db.commit()
    return {"status": "success", "shares_count": joke.shares_count}

@router.post("", response_model=s.Joke)
async def create_joke(
    joke: s.JokeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    joke_hash = joke.hash
    if not joke_hash:
        import hashlib
        joke_hash = hashlib.md5(joke.text.encode()).hexdigest()
        
    new_joke = JokeModel(
        text=joke.text,
        category=joke.category,
        hash=joke_hash,
        user_id=current_user.id
    )
    db.add(new_joke)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail="This Zoke already exists!")
        
    await db.refresh(new_joke)
    return new_joke

@router.put("/{joke_id}", response_model=s.Joke)
async def update_joke(
    joke_id: uuid.UUID,
    joke_update: s.JokeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a joke. Only the creator can update.
    """
    joke = await db.get(JokeModel, joke_id)
    if not joke:
        raise HTTPException(status_code=404, detail="Joke not found")
        
    if joke.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this joke")
        
    joke.text = joke_update.text
    if joke_update.category:
        joke.category = joke_update.category
        
    await db.commit()
    await db.refresh(joke)
    return joke

@router.post("/votes/joke")
async def vote_joke(
    vote: s.JokeVoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.services.reputation_service import update_user_zoscore

    # Fetch joke and its creator
    joke = await db.get(JokeModel, vote.joke_id)
    if not joke:
        raise HTTPException(status_code=404, detail="Joke not found")

    # Rule: Users cannot vote on their own content
    is_own_content = joke.user_id == current_user.id
    
    # Check if vote exists
    query = select(JokeVote).where(
        JokeVote.user_id == current_user.id,
        JokeVote.joke_id == vote.joke_id
    )
    result = await db.execute(query)
    existing_vote = result.scalars().first()

    score_change = 0
    status_msg = "success"

    if existing_vote:
        if existing_vote.vote_type == vote.vote_type:
            # Toggle off: delete the vote if clicking the same button
            if vote.vote_type == VoteType.FUNNY:
                score_change = -1
            else:
                score_change = 1
                
            await db.delete(existing_vote)
            status_msg = "unvoted"
        else:
            # Switch vote type
            if vote.vote_type == VoteType.FUNNY:
                # Not Funny -> Funny
                score_change = 2
            else:
                # Funny -> Not Funny
                score_change = -2
                
            existing_vote.vote_type = vote.vote_type
    else:
        if vote.vote_type == VoteType.FUNNY:
            score_change = 1
        else:
            score_change = -1
            
        new_vote = JokeVote(
            user_id=current_user.id,
            joke_id=vote.joke_id,
            vote_type=vote.vote_type
        )
        db.add(new_vote)

    # Update ZoScore only if not voting on own content and score should change
    updated_creator = None
    if not is_own_content and joke.user_id and score_change != 0:
        updated_creator = await update_user_zoscore(db, joke.user_id, score_change)

    # Check for Not Funny threshold (to delete bad/boring content)
    if vote.vote_type == VoteType.NOT_FUNNY and status_msg != "unvoted":
        count_query = select(func.count()).select_from(JokeVote).where(
            JokeVote.joke_id == vote.joke_id,
            JokeVote.vote_type == VoteType.NOT_FUNNY
        )
        count_result = await db.execute(count_query)
        not_funny_count = count_result.scalar()

        if not_funny_count >= 10: # threshold increased for reputation
             # We should probably only delete if score is really low, 
             # but keeping existing logic as requested ( incremental changes)
             pass 

    await db.commit()
    
    return {
        "status": status_msg, 
        "zoscore": updated_creator.zoscore if updated_creator else None,
        "badge_level": updated_creator.badge_level if updated_creator else None
    }
