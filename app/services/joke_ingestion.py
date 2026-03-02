import httpx
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.all_models import Joke
from app.db.session import AsyncSessionLocal
import logging
import asyncio

logger = logging.getLogger(__name__)

JOKE_API_URL = "https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,religious,political,racist,sexist&type=single&amount=10"

async def fetch_and_store_jokes():
    logger.info("Starting joke ingestion...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(JOKE_API_URL, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            jokes_data = data.get("jokes", [])
            if not jokes_data and not data.get("error"):
                 # Single joke response format varies
                 if "joke" in data:
                     jokes_data = [data]

            async with AsyncSessionLocal() as db:
                for j in jokes_data:
                    text = j.get("joke")
                    if not text:
                        continue
                    
                    # Create hash
                    joke_hash = hashlib.sha256(text.encode()).hexdigest()
                    
                    # Check existence
                    result = await db.execute(select(Joke).where(Joke.hash == joke_hash))
                    existing = result.scalars().first()
                    
                    if not existing:
                        new_joke = Joke(
                            text=text,
                            category=j.get("category", "General"),
                            hash=joke_hash,
                            source="jokeapi"
                        )
                        db.add(new_joke)
                        logger.info(f"Added new joke: {text[:20]}...")
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error fetching jokes: {e}")

async def main():
    logging.basicConfig(level=logging.INFO)
    await fetch_and_store_jokes()

if __name__ == "__main__":
    asyncio.run(main())
