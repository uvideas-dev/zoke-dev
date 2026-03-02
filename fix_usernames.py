import asyncio
import os
import random
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.all_models import User
from app.core.config import settings

async def fix():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        result = await db.execute(select(User).where(User.username == None))
        users = result.scalars().all()
        
        adjectives = ["Funny", "Crazy", "Happy", "Sad", "Silly", "Smart", "Cool"]
        nouns = ["Panda", "Tiger", "Lion", "Bear", "Dog", "Cat", "Bird"]
        
        for u in users:
            new_name = f"{random.choice(adjectives)}{random.choice(nouns)}{random.randint(10, 99)}"
            print(f"Updating {u.id} to {new_name}")
            u.username = new_name
            db.add(u)
            
        await db.commit()

if __name__ == "__main__":
    asyncio.run(fix())
