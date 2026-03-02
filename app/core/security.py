import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.all_models import User
from app.core.config import settings
import os

import json

# Initialize Firebase Admin
if not firebase_admin._apps:
    try:
        # 1. Try JSON content from environment variable (Best for Render)
        if settings.FIREBASE_CREDENTIALS_JSON:
            print("🚀 Initializing Firebase with JSON content from environment...")
            cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin SDK initialized with JSON content!")
            
        # 2. Try credential file (Best for local dev)
        elif os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
            print(f"✅ Loading Firebase credentials from: {settings.FIREBASE_CREDENTIALS_PATH}")
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin SDK initialized with file!")
            
        else:
            print(f"⚠️ Warning: No Firebase credentials found. Auth will fail.")
            pass
    except Exception as e:
        print(f"❌ Error initializing Firebase: {e}")
else:
    print("ℹ️  Firebase Admin SDK already initialized")

security = HTTPBearer(auto_error=False)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        # Verify Firebase Token
        decoded_token = auth.verify_id_token(token.credentials)
        firebase_uid = decoded_token['uid']
        
        # Check if user exists in DB
        result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
        user = result.scalars().first()

        # If not, create user (Lazy creation)
        if not user:
            user = User(firebase_uid=firebase_uid)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
        return user

    except Exception as e:
        await db.rollback()
        # In production, specific firebase exceptions should be caught
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Optional auth for public endpoints if needed, or anonymous
async def get_optional_user(
    db: AsyncSession = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(security)
) -> User | None:
    if not token or not token.credentials:
        return None
        
    try:
        # Verify Firebase Token manually here to avoid 401 exceptions from get_current_user
        decoded_token = auth.verify_id_token(token.credentials)
        firebase_uid = decoded_token['uid']
        
        # Check if user exists in DB
        result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
        user = result.scalars().first()

        # If not, create user (Lazy creation)
        if not user:
            user = User(firebase_uid=firebase_uid)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
        return user
    except Exception as e:
        print(f"ℹ️  Optional user token invalid or failed: {e}")
        return None
