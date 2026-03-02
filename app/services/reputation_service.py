import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.all_models import User

def calculate_badge(zoscore: int) -> str:
    """
    Calculate badge based on ZoScore.
    10 | Bronze
    100 | Silver
    1,000 | Gold
    10,000 | Platinum
    100,000 | Diamond
    """
    if zoscore >= 100000:
        return "diamond"
    elif zoscore >= 10000:
        return "platinum"
    elif zoscore >= 1000:
        return "gold"
    elif zoscore >= 100:
        return "silver"
    elif zoscore >= 10:
        return "bronze"
    return "new"

async def update_user_zoscore(db: AsyncSession, user_id: uuid.UUID, score_change: int):
    """
    Update a user's ZoScore incrementally and recalculate their badge.
    Everything is inside the existing transaction (if one is active).
    """
    if score_change == 0:
        return

    # Fetch user
    user = await db.get(User, user_id)
    if not user:
        return

    # Update score
    user.zoscore = (user.zoscore or 0) + score_change
    
    # Recalculate badge
    new_badge = calculate_badge(user.zoscore)
    user.badge_level = new_badge

    # The caller is responsible for db.commit()
    await db.flush()
    return user
