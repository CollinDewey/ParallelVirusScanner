import aiosqlite
import aiofiles
import asyncio
import logging
import hashlib
import os

db_path = os.path.join(os.path.dirname(__file__), "definitions.db")
logger = logging.getLogger(__name__)

def md5_hasher_worker(path):
    hasher = hashlib.md5()
    with open(path, "rb") as file:
        while chunk := file.read(16384):
            hasher.update(chunk)
    return hasher.hexdigest()

async def md5_scan(path, pool):
    if pool is not None:
        hash = await asyncio.get_running_loop().run_in_executor(pool, md5_hasher_worker, path)
    else:
        hasher = hashlib.md5()
        with aiofiles.open(path, "rb") as file:
            while chunk := file.read(16384):
                hasher.update(chunk)
        hash = hasher.hexdigest()

    logger.info(f"Hash: {hash}")

    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT * FROM definitions INDEXED BY md5_hash_index WHERE md5_hash = ?", (hash,)) as cursor:
            match = await cursor.fetchone()
            if match is not None:
                return True
    return False