import requests
import sqlite3
import logging
import hashlib
import os

db_path = os.path.join(os.path.dirname(__file__), "definitions.db")
logger = logging.getLogger(__name__)

def download_database():
    if os.path.exists(db_path): # Delete if exists
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            md5_hash TEXT NOT NULL
        )
    ''')
    cursor.execute("CREATE INDEX md5_hash_index ON definitions (md5_hash)")

    for i in range(488):
        if not logger.isEnabledFor(logging.INFO):
            print(".", end="", flush=True)
        logger.info(f"Downloading VirusShare_{i:05}.md5")
        
        while True:
            try:
                response = requests.get(f"https://virusshare.com/hashfiles/VirusShare_{i:05}.md5")
                response.raise_for_status()
                lines = response.text.splitlines()
                break
            except requests.RequestException as e:
                logger.error(f"Download of VirusShare_{i:05}.md5 failed, retrying...")
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                cursor.execute("INSERT INTO definitions (md5_hash) VALUES (?)", (line,))

    cursor.execute("DELETE FROM definitions WHERE md5_hash = ?", ("d41d8cd98f00b204e9800998ecf8427e",)) # Blank hash

    conn.commit()
    conn.close()

def validate_database():
    if os.path.exists(db_path):
        with open(db_path, "rb") as f:
            db_hash = hashlib.file_digest(f, hashlib.md5).hexdigest()
            logger.info(f"DB hash: {db_hash}")

        if db_hash == "464634b7490fa41d6c6d7684d5505992":
            logger.info("DB valid")
            return True
    else:
        logger.error("DB not found or invalid")
        return False

def init_database(bypass_checks):
    if bypass_checks:
        return

    if not validate_database():
        print("Downloading database (1.8GB)...\nThis will take some time.", end="", flush=True)
        download_database()
        if validate_database():
            print("\nDatabase downloaded.")
        else:
            print("\nDownload failed.\nRetrying...")
            #init_database(False)