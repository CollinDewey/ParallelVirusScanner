import argparse
import asyncio
import aiofiles
import logging
import os
from db import init_database
from scan import md5_scan

logger = logging.getLogger(__name__)

async def scan_dir(path, num_threads, mode, semaphore):
    tasks = []

    for root, dirs, files in os.walk(path):
        for file in files:
            tasks.append(asyncio.create_task(scan_file(os.path.join(root, file), mode, semaphore)))
    
    await asyncio.gather(*tasks)

async def scan_file(path, mode, semaphore):
    async with semaphore:
        logger.info(f"Scanning file: {path}")
        try:
            if os.path.isfile(path):
                async with aiofiles.open(path, "rb") as file:
                    match mode.lower():
                        case 'all':
                            if await md5_scan(file):
                                print(f"Virus found: {path}")
                        case 'md5':
                            if await md5_scan(file):
                                print(f"Virus found: {path}")
                        case 'zip':
                            pass
        except Exception as e:
            logger.error(f"Error scanning file {path}: {str(e)}") # Permissions probably

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=str, help='Path to the file or directory to scan')
    parser.add_argument('--num_threads', type=int, default=os.cpu_count(), help='Number of threads')
    parser.add_argument('--mode', type=str, default='all', choices=['all', 'md5', 'zip'], help='Scan Mode')
    parser.add_argument('--verbose', action='store_true', help='Set verbose mode')
    parser.add_argument('--bypass_checks', action='store_true', help='Bypasses validation checks')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.ERROR)

    if args.num_threads < 1:
        logger.error("Invalid number of threads")
        exit(1)

    # Initialize database and validate
    async def main():
        await init_database(args.bypass_checks)

        if os.path.isdir(args.path):
            logger.info(f"{args.path} is a directory")
            await scan_dir(args.path, args.num_threads, args.mode, asyncio.Semaphore(args.num_threads))
        elif os.path.isfile(args.path):  # One file, one thread
            logger.info(f"{args.path} is a file")
            await scan_file(args.path, args.mode, asyncio.Semaphore(1))
        else:  # Invalid path
            logger.error(f"{args.path} is not a directory or file")
            print('Invalid path')

    asyncio.run(main())