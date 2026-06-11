
import asyncio
import logging
from uuid import UUID
from app.core.database import db as db_manager

logger = logging.getLogger(__name__)

MEDCHEM_COLLECTION_ID = UUID("a1b2c3d4-0000-0000-0000-000000000001")
MEDCHEM_USER_ID = UUID("a1b2c3d4-0000-0000-0000-000000000002")

async def ensure_medchem_identity():
    """Ensure the MedChem system user and conversation exist."""
    logger.info("👤 Ensuring MedChem System Identity...")
    db = db_manager.get_client()
    
    # 1. Ensure User Exists
    try:
        user_res = db.table("users").select("id").eq("id", str(MEDCHEM_USER_ID)).execute()
        if not user_res.data:
            logger.info("  ➕ Creating MedChem System User...")
            db.table("users").insert({
                "id": str(MEDCHEM_USER_ID),
                "email": "medchem.system@benchside.app",
                "first_name": "MedChem",
                "last_name": "Knowledge Base",
                "password_hash": "system_account_no_password",
                "is_active": True,
                "is_admin": True,
                "is_verified": True
            }).execute()
        else:
            logger.info("  ✅ MedChem System User exists.")
    except Exception as e:
        logger.info(f"  ⚠️ Error ensuring user: {e}")

    # 2. Ensure Conversation Exists
    try:
        conv_res = db.table("conversations").select("id").eq("id", str(MEDCHEM_COLLECTION_ID)).execute()
        if not conv_res.data:
            logger.info("  ➕ Creating MedChem System Conversation...")
            db.table("conversations").insert({
                "id": str(MEDCHEM_COLLECTION_ID),
                "user_id": str(MEDCHEM_USER_ID),
                "title": "MedChem Knowledge Base Index",
                "is_pinned": True
            }).execute()
        else:
            logger.info("  ✅ MedChem System Conversation exists.")
    except Exception as e:
        logger.info(f"  ⚠️ Error ensuring conversation: {e}")

if __name__ == "__main__":
    asyncio.run(ensure_medchem_identity())
