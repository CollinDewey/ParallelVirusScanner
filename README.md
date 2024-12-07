# ParallelVirusScanner

Simple parallelized and multi-threaded MD5 virus scanner with block/cycle scheduling and PKZIP handling.

## Installing

To run, you'll need Python 3.

Install Dependencies with pip
```
pip install -r requirements.txt
```

On first startup, it downloads and builds a SQLlite definitions.db file. This takes a while to download and process.

## Testing

The [EICAR](https://www.eicar.org/download-anti-malware-testfile/) test file can be used for testing a correct identification, without placing malicious code on your computer.

To use, run the main.py with python and a file path through the command line. (Works on Windows, macOS, Linux)

```sh
python main.py <filename or file path>
```

## Usage

```sh
usage: main.py [-h] [--num_threads NUM_THREADS] [--verbose] [--bypass_checks] [--no_thread_creation] [--scheduling {block,cycle}] path

positional arguments:
  path                  Path to the file or directory to scan

options:
  -h, --help                  show this help message and exit
  --num_threads NUM_THREADS   Number of threads
  --verbose                   Set verbose mode
  --bypass_checks             Bypasses validation checks
  --no_thread_creation        Use one OS thread
  --scheduling {block,cycle}  Scheduling Type
```
## Contributers

This was a class final project for a Parallel Programming course. Created by Collin Dewey, Matthew Hood, and Joshua Johnson.
