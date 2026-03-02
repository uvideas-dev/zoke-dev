import asyncio
from app.db.session import AsyncSessionLocal
from app.models.all_models import Joke
from sqlalchemy import select, func

async def check_jokes():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(Joke.id)))
        count = result.scalar()
        print(f"Jokes in DB: {count}")
        
        if count == 0:
            print("No jokes found! Triggering ingestion...")
            from app.services.joke_ingestion import fetch_and_store_jokes
            await fetch_and_store_jokes()
            
            result = await session.execute(select(func.count(Joke.id)))
            count = result.scalar()
            print(f"Jokes in DB after ingestion: {count}")

if __name__ == "__main__":
    asyncio.run(check_jokes())
