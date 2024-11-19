import requests
import sqlite3
import logging
import hashlib
import aiohttp
import asyncio
import aiosqlite
import os

db_path = os.path.join(os.path.dirname(__file__), "definitions.db")
logger = logging.getLogger(__name__)

async def download_file(session, file_index):
    """Download a single hash file."""
    url = f"https://virusshare.com/hashfiles/VirusShare_{file_index:05}.md5"
    logger.info(f"Starting download for VirusShare_{file_index:05}.md5")
    while True:
        try:
            async with session.get(url, ssl=False) as response:
                response.raise_for_status()
                logger.info(f"Successfully downloaded VirusShare_{file_index:05}.md5")
                return (file_index, (await response.text()).splitlines())
        except aiohttp.ClientError as e:
            logger.error(f"Download of VirusShare_{file_index:05}.md5 failed: {e}. Retrying...")

async def process_file(file_index, lines, conn):
    """Process and insert hash lines into the database."""
    logger.info(f"Processing file VirusShare_{file_index:05}.md5 with {len(lines)} lines")
    async with conn.cursor() as cursor:
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                await cursor.execute("INSERT INTO definitions (md5_hash) VALUES (?)", (line,))
        await conn.commit()
    logger.info(f"Finished processing VirusShare_{file_index:05}.md5")

async def worker(task_queue, conn, session):
    """Worker to download and process files."""
    while not task_queue.empty():
        file_index = await task_queue.get()
        try:
            logger.info(f"Worker started on file VirusShare_{file_index:05}.md5")
            file_index, lines = await download_file(session, file_index)
            await process_file(file_index, lines, conn)
        except Exception as e:
            logger.error(f"Error processing file VirusShare_{file_index:05}: {e}")
        finally:
            task_queue.task_done()
            logger.info(f"Worker finished with file VirusShare_{file_index:05}.md5")

async def download_database():
    if os.path.exists(db_path):  # Delete if exists
        logger.info("Removing existing database file")
        os.remove(db_path)

    logger.info("Creating new database")
    # Create database and definitions table
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                md5_hash TEXT NOT NULL
            )
        ''')
        await conn.execute("CREATE INDEX IF NOT EXISTS md5_hash_index ON definitions (md5_hash)")
        await conn.commit()
    logger.info("Database and table setup complete")

    # Create task queue
    task_queue = asyncio.Queue()
    for i in range(488):
        await task_queue.put(i)

    logger.info("Task queue populated with 488 tasks")

    # Create workers for downloading and processing
    async with aiohttp.ClientSession() as session:
        async with aiosqlite.connect(db_path) as conn:
            workers = [
                asyncio.create_task(worker(task_queue, conn, session))
                for _ in range(10)  # Adjust number of workers as needed
            ]
            logger.info("Workers started for database download and processing")
            await task_queue.join()
            logger.info("All tasks completed. Cleaning up workers")
            for w in workers:
                w.cancel()

    # Remove blank hash
    async with aiosqlite.connect(db_path) as conn:
        logger.info("Removing blank hash from database")
        await conn.execute("DELETE FROM definitions WHERE md5_hash = ?", ("d41d8cd98f00b204e9800998ecf8427e",))
        await conn.commit()

    logger.info("Database download and setup complete.")

async def validate_database():
    """Validate the database by checking the number of elements."""
    expected_count = 41746428  # Expected size (10 million minus the blank hash)

    if os.path.exists(db_path):
        async with aiosqlite.connect(db_path) as conn:
            async with conn.execute("SELECT COUNT(*) FROM definitions") as cursor:
                count = await cursor.fetchone()
                if count and count[0] == expected_count:
                    logger.info(f"DB is valid with {count[0]} entries.")
                    return True
                else:
                    logger.error(f"DB invalid: expected {expected_count} entries but found {count[0]}")
                    return False
    else:
        logger.error("DB not found")
        return False
    
async def init_database(bypass_checks):
    """Initialize the database, validating its integrity and downloading if needed."""
    if bypass_checks:
        logger.info("Bypassing database checks.")
        return

    logger.info("Validating database...")
    is_valid = await validate_database()  # Use the updated validate_database function

    if not is_valid:
        print("Downloading database (1.8GB)...\nThis will take some time.", end="", flush=True)
        await download_database()  # Use the updated download_database function
        is_valid = await validate_database()

        if is_valid:
            print("\nDatabase downloaded and validated successfully.")
        else:
            print("\nDownload failed. Please check your network connection or retry.")
            logger.error("Database download and validation failed.")
            return
    else:
        logger.info("Database is already valid.")

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    #download_database()
    asyncio.run(download_database())