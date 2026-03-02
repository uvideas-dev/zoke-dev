import asyncio
import asyncpg

async def setup_db():
    print("Attempting to connect to 'postgres' database as user 'varma' without password...")
    try:
        # Try connecting to 'postgres' db first
        conn = await asyncpg.connect(user='varma', database='postgres', host='localhost', port=5433)
        print("✅ Connected to 'postgres' database.")
    except Exception as e:
        print(f"⚠️ Could not connect to 'postgres': {e}")
        try:
            # Try connecting to 'template1'
            print("Attempting to connect to 'template1' database...")
            conn = await asyncpg.connect(user='varma', database='template1', host='localhost', port=5433)
            print("✅ Connected to 'template1' database.")
        except Exception as e2:
            print(f"❌ Could not connect to 'template1': {e2}")
            return

    try:
        # Set password
        print("Setting password for user 'varma' to 'varma123'...")
        await conn.execute("ALTER USER varma WITH PASSWORD 'varma123';")
        print("✅ Password updated.")

        # Create database zoke_db
        print("Checking if 'zoke_db' exists...")
        result = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'zoke_db'")
        if not result:
            print("Creating 'zoke_db'...")
            await conn.execute("CREATE DATABASE zoke_db;")
            print("✅ Database 'zoke_db' created.")
        else:
            print("✅ 'zoke_db' already exists.")

    except Exception as e:
        print(f"❌ Error during setup: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(setup_db())
