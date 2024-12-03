import argparse
import concurrent.futures
import asyncio
import logging
import os
import zipfile
import shutil
import tempfile
from itertools import cycle
from db import init_database
from scan import md5_scan

logger = logging.getLogger(__name__)

#################################################################
## Extracts Zip Archive to Temporary Directory
def extract_zip(zip_path, tmp_dir):
    try:
        logger.info(f"Detected ZIP file: {zip_path}")
        # Save the ZIP file to the TMP directory
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            tmp_zip_path = os.path.join(tmp_dir, os.path.basename(zip_path))
            logger.info(f"Extracting ZIP file: {zip_path} into TMP directory")
            zip_ref.extractall(tmp_zip_path)
        logger.info(f"Extraction complete for: {zip_path}")
        return True
    except Exception as e:
        logger.error(f"Error processing ZIP file: {zip_path}. Exception: {e}")
        return False
    

#################################################################
## Scans Directory with Block Scheduling
async def scan_dir_with_block(path, num_threads, mode, semaphore, true_path, pool):
    tasks = []
    tmp_dir = tempfile.mkdtemp()
    scan_tmp = False

    for root, dirs, files in os.walk(path):
        for file in files:

            if zipfile.is_zipfile(os.path.join(root, file)):
                is_extracted = extract_zip(os.path.join(root, file), tmp_dir)
                
                if scan_tmp == False and is_extracted == True:
                    scan_tmp = True
            else:
                tasks.append(asyncio.create_task(scan_file(os.path.join(root, file), mode, semaphore, pool, true_path)))
    
    if scan_tmp:
        logger.info(f"Scanning extracted files in TMP directory: {tmp_dir}")
        await scan_dir_with_block(tmp_dir, num_threads, mode, semaphore, true_path, pool)

    await asyncio.gather(*tasks)

    if scan_tmp:
        try:
            shutil.rmtree(tmp_dir)
            logger.info(f"Deleted TMP directory: {tmp_dir}")
        except Exception as e:
            logger.error(f"Error deleting TMP directory: {e}")


#################################################################
## Scans Directory with Cycle Scheduling
async def scan_dir_with_cycle_scheduling(path, num_threads, mode, true_path, pool):
    tmp_dir = tempfile.mkdtemp()
    scan_tmp = False

    # Prep for cycle scheduling
    tasks_per_worker = {i: [] for i in range(num_threads)}
    workers = cycle(range(num_threads))

    for root, dirs, files in os.walk(path):
        for file in files:
            if zipfile.is_zipfile(os.path.join(root, file)):
                is_extracted = extract_zip(os.path.join(root, file), tmp_dir)
                
                if scan_tmp == False and is_extracted == True:
                    scan_tmp = True
            else:
                worker_id = next(workers)  # Assign task to the next worker in cycle
                tasks_per_worker[worker_id].append(os.path.join(root, file))

    if scan_tmp:
        logger.info(f"Scanning extracted files in TMP directory: {tmp_dir}")
        await scan_dir_with_cycle_scheduling(tmp_dir, num_threads, mode, true_path, pool)

    # Run tasks for each worker
    semaphores = [asyncio.Semaphore(1) for _ in range(num_threads)]
    worker_tasks = [
        asyncio.create_task(scan_worker(tasks, mode, semaphores[i], pool, true_path))
        for i, tasks in tasks_per_worker.items()
    ]
    await asyncio.gather(*worker_tasks)

    if scan_tmp:
        try:
            shutil.rmtree(tmp_dir)
            logger.info(f"Deleted TMP directory: {tmp_dir}")
        except Exception as e:
            logger.error(f"Error deleting TMP directory: {e}")


#################################################################
## Worker to process a list of files
async def scan_worker(tasks, mode, semaphore, pool, true_path):
    for task in tasks:
        await scan_file(task, mode, semaphore, pool, true_path)


#################################################################
## Scans a file for a virus using a database of md5 hashes
async def scan_file(path, mode, semaphore, pool, true_path):
    async with semaphore:
        logger.info(f"Scanning file: {path}")
        try:
            if os.path.isfile(path):
                match mode.lower():
                    case 'dir':
                        if await md5_scan(path, pool):
                            print(f"Virus found inside directory \"{true_path}\": {os.path.basename(path)}")
                    case 'zip':
                        if await md5_scan(path, pool):
                            print(f"Virus found inside zip file \"{true_path}\": {os.path.basename(path)}")
                    case 'file':
                        if await md5_scan(path, pool):
                            print(f"Virus found: {true_path}")
        except Exception as e:
            logger.error(f"Error scanning file {path}: {str(e)}") # Permissions probably


#################################################################
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=str, help='Path to the file or directory to scan')
    parser.add_argument('--num_threads', type=int, default=os.cpu_count(), help='Number of threads')
    parser.add_argument('--verbose', action='store_true', help='Set verbose mode')
    parser.add_argument('--bypass_checks', action='store_true', help='Bypasses validation checks')
    parser.add_argument('--no_thread_creation', action='store_true', help='Use one OS thread')
    parser.add_argument('--scheduling', type=str, default='block', choices=['block', 'cycle'], help='Scheduling Type')


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
        logger.info(f"using {args.num_threads} threads")
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=args.num_threads) if not args.no_thread_creation else None


        # If path is a directory
        if os.path.isdir(args.path):
            logger.info(f"{args.path} is a directory")
            if args.scheduling == "block":
                logger.info(f"using block scheduling")
                await scan_dir_with_block(args.path, args.num_threads, 'dir', asyncio.Semaphore(args.num_threads), args.path, pool)
            else:
                logger.info(f"using cycle scheduling")
                await scan_dir_with_cycle_scheduling(args.path, args.num_threads, 'dir', args.path, pool)

        # If path is a zip file
        elif zipfile.is_zipfile(args.path):
            logger.info(f"{args.path} is a zip file")
            tmp_dir = tempfile.mkdtemp()
            is_extracted = extract_zip(args.path, tmp_dir)

            if is_extracted:
                logger.info(f"Scanning extracted files in TMP directory: {tmp_dir}")
                
                if args.scheduling == "block":
                    logger.info(f"using block scheduling")
                    await scan_dir_with_block(tmp_dir, args.num_threads, 'zip', asyncio.Semaphore(args.num_threads), args.path, pool)
                else:
                    logger.info(f"using cycle scheduling")
                    await scan_dir_with_cycle_scheduling(tmp_dir, args.num_threads, 'zip', args.path, pool)

                try:
                    shutil.rmtree(tmp_dir)
                    logger.info(f"Deleted TMP directory: {tmp_dir}")
                except Exception as e:
                    logger.error(f"Error deleting TMP directory: {e}")

        # If path is an individual file
        elif os.path.isfile(args.path):
            logger.info(f"{args.path} is a file")
            await scan_file(args.path, 'file', asyncio.Semaphore(1), None, args.path)

        # If path is invalid
        else:
            logger.error(f"{args.path} is not a directory or file")
            print('Invalid path')

    asyncio.run(main())
