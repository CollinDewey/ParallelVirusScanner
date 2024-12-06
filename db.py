import logging
import aiohttp
import asyncio
import aiosqlite
import os

db_path = os.path.join(os.path.dirname(__file__), "definitions.db")
logger = logging.getLogger(__name__)

async def download_id(id, db, semaphore):
    async with semaphore:
        if not logger.isEnabledFor(logging.INFO):
                print(".", end="", flush=True)
        logger.info(f"Downloading VirusShare_{id:05}.md5")
        
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://virusshare.com/hashfiles/VirusShare_{id:05}.md5") as response:
                        response.raise_for_status()
                        query = "INSERT INTO definitions (md5_hash) VALUES " + ", ".join([f"('{line}')" for line in (await response.text()).splitlines() if line and not line.startswith('#')])
                        break
            except Exception:
                logger.error(f"Download of VirusShare_{id:05}.md5 failed, retrying...")
    
        logger.info(f"Processing of {id} started")
        async with db.cursor() as cursor:
            await cursor.execute(query)
        await db.commit()
        logger.info(f"Processing of {id} complete")

async def download_database():
    if os.path.exists(db_path): # Delete if exists
        logger.info(f"Deleting DB")
        os.remove(db_path)

    async with aiosqlite.connect(":memory:") as db:
        async with db.cursor() as cursor:
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS definitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    md5_hash TEXT NOT NULL
                )
            ''')
            await cursor.execute("CREATE INDEX md5_hash_index ON definitions (md5_hash)")
            await db.execute("PRAGMA journal_mode = OFF;")
            await db.execute("PRAGMA synchronous = 0;")
            await db.execute("PRAGMA cache_size = 1000000;")
            await db.execute("PRAGMA locking_mode = EXCLUSIVE;")
            await db.execute("PRAGMA temp_store = MEMORY;")
            await db.commit()

            logger.info(f"Starting download...")
            semaphore = asyncio.Semaphore(8)
            tasks = [asyncio.create_task(download_id(i, db, semaphore)) for i in range(488)]
            await asyncio.gather(*tasks)
            logger.info(f"Download finished processing.")

            await cursor.execute("DELETE FROM definitions WHERE md5_hash = ?", ("d41d8cd98f00b204e9800998ecf8427e",)) # Blank hash
        await db.commit()
        async with aiosqlite.connect(db_path) as file_db:
                await db.backup(file_db)
        await db.close()
    

async def validate_database():
    if not os.path.exists(db_path):
        logger.error("DB not found")
        return False

    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM definitions") as cursor:
                count = await cursor.fetchone()
                if count and count[0] == 41746428:
                    return True
    except Exception:
        logger.error(f"DB invalid")

    return False

async def init_database(bypass_checks):
    if bypass_checks:
        return

    if not await validate_database():
        print("Downloading database...\nThis will take some time.", end="", flush=True)
        await download_database()
        if await validate_database():
            print("\nDatabase downloaded.")
        else:
            print("\nDownload failed.\nRetrying...")
            await init_database(False)