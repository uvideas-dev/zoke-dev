import asyncio
import asyncpg
import os

async def check_creds():
    # List of common credentials to try. 
    # Format: (user, password, database)
    # We try connecting to 'postgres' db first to verify creds, then check for zoke_db
    
    attempts = [
        ("postgres", "postgres", "postgres"),
        ("postgres", "password", "postgres"),
        ("postgres", "", "postgres"),
        ("varma", "", "postgres"), # Often mac user with no pass
        ("varma", "postgres", "postgres"),
    ]

    print("Diagnosing Database Connection...")
    working_creds = None

    for user, password, db_name in attempts:
        print(f"Trying User='{user}', Pass='{'*' if password else '<empty>'}', DB='{db_name}'...")
        try:
            conn = await asyncpg.connect(user=user, password=password, database=db_name, host='localhost')
            print(f"✅ SUCCESS! Connected with User='{user}', Pass='{'*' if password else '<empty>'}'")
            working_creds = (user, password)
            await conn.close()
            break
        except Exception as e:
            print(f"❌ Failed: {e}")

    if working_creds:
        user, password = working_creds
        print(f"\nVerifying if 'zoke_db' exists...")
        try:
            conn = await asyncpg.connect(user=user, password=password, database='zoke_db', host='localhost')
            print("✅ 'zoke_db' exists and is accessible.")
            await conn.close()
            print(f"\nRECOMMENDED DATABASE_URL: postgresql+asyncpg://{user}:{password}@localhost/zoke_db")
        except asyncpg.results.InvalidCatalogNameError:
            print("❌ 'zoke_db' database does not exist.")
            print("Attempting to create 'zoke_db'...")
            try:
                # Connect to postgres db to create zoke_db
                conn = await asyncpg.connect(user=user, password=password, database='postgres', host='localhost')
                await conn.execute('CREATE DATABASE zoke_db')
                await conn.close()
                print("✅ Created 'zoke_db'.")
                print(f"\nRECOMMENDED DATABASE_URL: postgresql+asyncpg://{user}:{password}@localhost/zoke_db")
            except Exception as e:
                print(f"❌ Could not create database: {e}")
    else:
        print("\n❌ Could not find working credentials. Please check your Postgres installation.")

if __name__ == "__main__":
    asyncio.run(check_creds())
