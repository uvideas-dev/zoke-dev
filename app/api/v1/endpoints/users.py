from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from app.db.session import get_db
from app.core.security import get_current_user, get_optional_user
from app.models.all_models import User, Follow, SavedJoke, Joke, ReZoKe, ReZoKeVote
from app.schemas import schemas as s
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import selectinload

router = APIRouter()

async def get_user_stats(db: AsyncSession, user: User):
    # Count Zokers (Followers)
    zokers_query = select(func.count()).select_from(Follow).where(Follow.followed_id == user.id)
    zokers_result = await db.execute(zokers_query)
    zokers_count = zokers_result.scalar()

    # Count Zoking (Following)
    zoking_query = select(func.count()).select_from(Follow).where(Follow.follower_id == user.id)
    zoking_result = await db.execute(zoking_query)
    zoking_count = zoking_result.scalar()

    return zokers_count, zoking_count

@router.get("/me", response_model=s.User)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        zokers_count, zoking_count = await get_user_stats(db, current_user)
        
        # We need to ensure the object returned to the schema has these fields
        # since they are in s.User but not in the SQL model
        current_user.zokers_count = zokers_count
        current_user.zoking_count = zoking_count
        current_user.is_following = False
        
        return current_user
    except Exception as e:
        print(f"Error in get_me: {e}")
        raise HTTPException(status_code=500, detail="Error fetching profile stats")

@router.put("/me", response_model=s.User)
async def update_me(
    user_update: s.UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if user_update.username is not None:
        current_user.username = user_update.username
    if user_update.bio is not None:
        current_user.bio = user_update.bio
    if user_update.emoji_avatar is not None:
        current_user.emoji_avatar = user_update.emoji_avatar
        
    await db.commit()
    await db.refresh(current_user)
    
    zokers_count, zoking_count = await get_user_stats(db, current_user)
    current_user.zokers_count = zokers_count
    current_user.zoking_count = zoking_count
    current_user.is_following = False
    
    return current_user

@router.post("/{user_id}/zoke")
async def join_zokers(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cant join your own Zokers!")
        
    # Check if already following
    query = select(Follow).where(Follow.follower_id == current_user.id, Follow.followed_id == user_id)
    result = await db.execute(query)
    if result.scalars().first():
        return {"status": "already_following"}
        
    new_follow = Follow(follower_id=current_user.id, followed_id=user_id)
    db.add(new_follow)
    await db.commit()
    return {"status": "success"}

@router.delete("/{user_id}/zoke")
async def leave_zokers(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Follow).where(Follow.follower_id == current_user.id, Follow.followed_id == user_id)
    result = await db.execute(query)
    follow = result.scalars().first()
    
    if follow:
        await db.delete(follow)
        await db.commit()
        
    return {"status": "success"}

@router.get("/me/created", response_model=List[s.Joke])
async def get_my_jokes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy.orm import selectinload
    query = select(Joke).where(Joke.user_id == current_user.id).options(selectinload(Joke.user)).order_by(desc(Joke.created_at))
    result = await db.execute(query)
    jokes = list(result.scalars().all())
    from app.api.v1.endpoints.jokes import enrich_joke_stats
    await enrich_joke_stats(db, jokes)
    return jokes

@router.get("/me/rezokes", response_model=List[s.ReZoKe])
async def get_my_rezokes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(ReZoKe)
        .where(ReZoKe.user_id == current_user.id)
        .options(
            selectinload(ReZoKe.joke).selectinload(Joke.user),
            selectinload(ReZoKe.user)
        )
        .order_by(desc(ReZoKe.created_at))
    )
    result = await db.execute(query)
    rezokes = list(result.scalars().all())
    
    # Enrich user_vote for ReZoKes
    if rezokes:
        rz_ids = [r.id for r in rezokes]
        uv_q = select(ReZoKeVote.rezoke_id, ReZoKeVote.vote_type).where(
            ReZoKeVote.rezoke_id.in_(rz_ids), ReZoKeVote.user_id == current_user.id
        )
        uv_res = await db.execute(uv_q)
        uv_map = {r[0]: r[1] for r in uv_res.all()}
        for r in rezokes:
            r.user_vote = uv_map.get(r.id)
            
    return rezokes

@router.get("/me/saved", response_model=List[s.Joke])
async def get_saved_jokes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy.orm import selectinload
    query = select(Joke).join(SavedJoke, Joke.id == SavedJoke.joke_id).where(SavedJoke.user_id == current_user.id).options(selectinload(Joke.user)).order_by(desc(SavedJoke.created_at))
    result = await db.execute(query)
    jokes = list(result.scalars().all())
    from app.api.v1.endpoints.jokes import enrich_joke_stats
    await enrich_joke_stats(db, jokes)
    return jokes

@router.post("/save/{joke_id}")
async def save_joke(
    joke_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if already saved
    query = select(SavedJoke).where(SavedJoke.user_id == current_user.id, SavedJoke.joke_id == joke_id)
    result = await db.execute(query)
    if result.scalars().first():
        return {"status": "already_saved"}
        
    new_save = SavedJoke(user_id=current_user.id, joke_id=joke_id)
    db.add(new_save)
    await db.commit()
    return {"status": "success"}

@router.get("/search", response_model=List[s.User])
async def search_users(
    query: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search users by username.
    """
    if not query:
        return []
        
    stmt = select(User).where(
        User.username.ilike(f"%{query}%"),
        User.id != current_user.id
    ).limit(20)
    
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    # Enrich with stats
    if current_user:
        followed_subquery = select(Follow.followed_id).where(Follow.follower_id == current_user.id)
        followed_result = await db.execute(followed_subquery)
        followed_ids = set(followed_result.scalars().all())
    else:
        followed_ids = set()

    for user in users:
         zokers_count, zoking_count = await get_user_stats(db, user)
         user.zokers_count = zokers_count
         user.zoking_count = zoking_count
         user.is_following = user.id in followed_ids
         
    return users

@router.get("/suggestions", response_model=List[s.User])
async def get_suggested_users(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get suggested users to follow ("Users with ZoKe").
    Simple logic: Users not followed by current user.
    """
    # Subquery for users already followed
    followed_subquery = select(Follow.followed_id).where(Follow.follower_id == current_user.id)
    
    # Select users NOT in followed properties AND not self
    stmt = select(User).where(
        User.id.not_in(followed_subquery),
        User.id != current_user.id
    ).order_by(func.random()).limit(limit)
    
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    # Enrich with stats
    for user in users:
         zokers_count, zoking_count = await get_user_stats(db, user)
         user.zokers_count = zokers_count
         user.zoking_count = zoking_count
         user.is_following = False
         
    return users

@router.get("/{user_id}/zokers", response_model=List[s.User])
async def get_zokers(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user)
):
    """
    Get users who follow the target user.
    """
    user_uuid = None
    try:
        from uuid import UUID
        user_uuid = UUID(user_id)
    except:
        # Resolve to UUID first
        q = select(User.id).where(User.firebase_uid == user_id)
        res = await db.execute(q)
        user_uuid = res.scalar()
        
    if not user_uuid:
        return []

    stmt = select(User).join(Follow, Follow.follower_id == User.id).where(Follow.followed_id == user_uuid)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    if current_user:
        followed_subquery = select(Follow.followed_id).where(Follow.follower_id == current_user.id)
        followed_result = await db.execute(followed_subquery)
        followed_ids = set(followed_result.scalars().all())
    else:
        followed_ids = set()

    for user in users:
         zokers_count, zoking_count = await get_user_stats(db, user)
         user.zokers_count = zokers_count
         user.zoking_count = zoking_count
         user.is_following = user.id in followed_ids
         
    return users

@router.get("/{user_id}/zoking", response_model=List[s.User])
async def get_zoking(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user)
):
    """
    Get users whom the target user follows.
    """
    user_uuid = None
    try:
        from uuid import UUID
        user_uuid = UUID(user_id)
    except:
        q = select(User.id).where(User.firebase_uid == user_id)
        res = await db.execute(q)
        user_uuid = res.scalar()

    if not user_uuid:
        return []

    stmt = select(User).join(Follow, Follow.followed_id == User.id).where(Follow.follower_id == user_uuid)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    if current_user:
        followed_subquery = select(Follow.followed_id).where(Follow.follower_id == current_user.id)
        followed_result = await db.execute(followed_subquery)
        followed_ids = set(followed_result.scalars().all())
    else:
        followed_ids = set()

    for user in users:
         zokers_count, zoking_count = await get_user_stats(db, user)
         user.zokers_count = zokers_count
         user.zoking_count = zoking_count
         user.is_following = user.id in followed_ids
         
    return users

@router.get("/{user_id}", response_model=s.User)
async def get_user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user)
):
    user = None
    try:
        from uuid import UUID
        u_id = UUID(user_id)
        user = await db.get(User, u_id)
    except (ValueError, ImportError):
        # Maybe it's a firebase_uid
        query = select(User).where(User.firebase_uid == user_id)
        result = await db.execute(query)
        user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    zokers_count, zoking_count = await get_user_stats(db, user)
    user.zokers_count = zokers_count
    user.zoking_count = zoking_count

    if current_user:
        query = select(Follow).where(Follow.follower_id == current_user.id, Follow.followed_id == user.id)
        result = await db.execute(query)
        user.is_following = result.scalars().first() is not None
    else:
        user.is_following = False

    return user

@router.get("/{user_id}/jokes", response_model=List[s.Joke])
async def get_user_jokes(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user)
):
    user_uuid = None
    try:
        from uuid import UUID
        user_uuid = UUID(user_id)
    except:
        q = select(User.id).where(User.firebase_uid == user_id)
        res = await db.execute(q)
        user_uuid = res.scalar()

    if not user_uuid:
        return []

    from sqlalchemy.orm import selectinload
    query = select(Joke).where(Joke.user_id == user_uuid).options(selectinload(Joke.user)).order_by(desc(Joke.created_at))
    result = await db.execute(query)
    jokes = list(result.scalars().all())
    from app.api.v1.endpoints.jokes import enrich_joke_stats
    await enrich_joke_stats(db, jokes)
    return jokes

@router.get("/{user_id}/rezokes", response_model=List[s.ReZoKe])
async def get_user_rezokes(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_requester: User = Depends(get_optional_user)
):
    user_uuid = None
    try:
        from uuid import UUID
        user_uuid = UUID(user_id)
    except:
        q = select(User.id).where(User.firebase_uid == user_id)
        res = await db.execute(q)
        user_uuid = res.scalar()

    if not user_uuid:
        return []

    query = (
        select(ReZoKe)
        .where(ReZoKe.user_id == user_uuid)
        .options(
            selectinload(ReZoKe.joke).selectinload(Joke.user),
            selectinload(ReZoKe.user)
        )
        .order_by(desc(ReZoKe.created_at))
    )
    result = await db.execute(query)
    rezokes = list(result.scalars().all())
    
    # Enrich user_vote if there is a logged in user (optional)
    if current_requester and rezokes:
        rz_ids = [r.id for r in rezokes]
        uv_q = select(ReZoKeVote.rezoke_id, ReZoKeVote.vote_type).where(
            ReZoKeVote.rezoke_id.in_(rz_ids), ReZoKeVote.user_id == current_requester.id
        )
        uv_res = await db.execute(uv_q)
        uv_map = {r[0]: r[1] for r in uv_res.all()}
        for r in rezokes:
            r.user_vote = uv_map.get(r.id)

    return rezokes
