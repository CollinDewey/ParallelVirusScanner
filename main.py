import argparse
import asyncio
import aiofiles
import logging
import os
import zipfile
import shutil
import tempfile
from itertools import cycle
from db import init_database
from scan import md5_scan

logger = logging.getLogger(__name__)

async def scan_dir(path, num_threads, mode, semaphore):
    tasks = []
    tmp_dir = tempfile.mkdtemp()
    scan_tmp = False

    for root, dirs, files in os.walk(path):
        for file in files:

            if zipfile.is_zipfile(os.path.join(root, file)):
                    try:
                        logger.info(f"Detected ZIP file: {os.path.join(root, file)}")
                        # Save the ZIP file to the TMP directory
                        with zipfile.ZipFile(os.path.join(root, file), 'r') as zip_ref:
                            tmp_zip_path = os.path.join(tmp_dir, os.path.basename(file))
                            logger.info(f"Extracting ZIP file: {os.path.join(root, file)} into TMP directory")
                            zip_ref.extractall(tmp_zip_path)
                        logger.info(f"Extraction complete for: {os.path.join(root, file)}")
                        scan_tmp = True
                    except Exception as e:
                        logger.error(f"Error processing ZIP file: {os.path.join(root, file)}. Exception: {e}")
            else:
                tasks.append(asyncio.create_task(scan_file(os.path.join(root, file), mode, semaphore)))
    
    if scan_tmp:
        logger.info(f"Scanning {tmp_dir}")
        await scan_dir(tmp_dir, num_threads, mode, semaphore)

    await asyncio.gather(*tasks)

    if scan_tmp:
        try:
            shutil.rmtree(tmp_dir)
            logger.info(f"Deleted TMP directory: {tmp_dir}")
        except Exception as e:
            logger.error(f"Error deleting TMP directory: {e}")

async def scan_dir_with_cycle_scheduling(path, num_threads, mode):
    tmp_dir = tempfile.mkdtemp()
    scan_tmp = False

    # Prep for cycle scheduling
    tasks_per_worker = {i: [] for i in range(num_threads)}
    workers = cycle(range(num_threads))

    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)

            if zipfile.is_zipfile(file_path):
                try:
                    logger.info(f"Detected ZIP file: {file_path}")
                    # Extract ZIP file into the TMP directory
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        logger.info(f"Extracting ZIP file: {file_path} into TMP directory")
                        zip_ref.extractall(tmp_dir)
                    logger.info(f"Extraction complete for: {file_path}")
                    scan_tmp = True
                except Exception as e:
                    logger.error(f"Error processing ZIP file: {file_path}. Exception: {e}")
            else:
                worker_id = next(workers)  # Assign task to the next worker in cycle
                tasks_per_worker[worker_id].append(file_path)

    if scan_tmp:
        logger.info(f"Scanning extracted files in TMP directory: {tmp_dir}")
        await scan_dir_with_cycle_scheduling(tmp_dir, num_threads, mode)

    # Run tasks for each worker
    semaphores = [asyncio.Semaphore(1) for _ in range(num_threads)]
    worker_tasks = [
        asyncio.create_task(scan_worker(tasks, mode, semaphores[i]))
        for i, tasks in tasks_per_worker.items()
    ]
    await asyncio.gather(*worker_tasks)

    if scan_tmp:
        try:
            shutil.rmtree(tmp_dir)
            logger.info(f"Deleted TMP directory: {tmp_dir}")
        except Exception as e:
            logger.error(f"Error deleting TMP directory: {e}")


async def scan_worker(tasks, mode, semaphore):
    # Worker to process a list of files
    for task in tasks:
        await scan_file(task, mode, semaphore)


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

        if os.path.isdir(args.path):
            logger.info(f"{args.path} is a directory")
            if args.scheduling == "block":
                logger.info(f"using block scheduling")
                await scan_dir(args.path, args.num_threads, args.mode, asyncio.Semaphore(args.num_threads))
            else:
                logger.info(f"using cycle scheduling")
                await scan_dir_with_cycle_scheduling(args.path, args.num_threads, args.mode)
        elif os.path.isfile(args.path):  # One file, one thread
            logger.info(f"{args.path} is a file")
            await scan_file(args.path, args.mode, asyncio.Semaphore(1))
        else:  # Invalid path
            logger.error(f"{args.path} is not a directory or file")
            print('Invalid path')

    asyncio.run(main())