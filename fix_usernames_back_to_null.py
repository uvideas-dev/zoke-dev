import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.all_models import User
import re

from app.core.config import settings

async def revert():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    adjectives = ["Funny", "Crazy", "Happy", "Sad", "Silly", "Smart", "Cool"]
    nouns = ["Panda", "Tiger", "Lion", "Bear", "Dog", "Cat", "Bird"]
    
    # Create regex pattern for the names I generated
    adj_pattern = "|".join(adjectives)
    noun_pattern = "|".join(nouns)
    
    # e.g., FunnyPanda12
    pattern = re.compile(f"^({adj_pattern})({noun_pattern})[0-9]{{2}}$")
    
    async with async_session() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        count = 0
        for u in users:
            if u.username and pattern.match(u.username):
                print(f"Reverting {u.username} (ID: {u.id}) back to null")
                u.username = None
                db.add(u)
                count += 1
                
        if count > 0:
            await db.commit()
            print(f"Reverted {count} usernames.")
        else:
            print("No matching usernames found.")

if __name__ == "__main__":
    asyncio.run(revert())
