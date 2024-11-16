import aiosqlite
import asyncio
import logging
import hashlib
import os

db_path = os.path.join(os.path.dirname(__file__), "definitions.db")
logger = logging.getLogger(__name__)

async def md5_scan(file):
    hasher = hashlib.md5()
    while chunk := await file.read(16384):
        hasher.update(chunk)
    logger.info(f"Hash: {hasher.hexdigest()}")

    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT * FROM definitions INDEXED BY md5_hash_index WHERE md5_hash = ?", (hasher.hexdigest(),)) as cursor:
            match = await cursor.fetchone()
            if match is not None:
                return True
    return False