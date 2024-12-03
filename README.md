# ParallelVirusScanner

Install Dependencies with pip
```
pip install -r requirements.txt
```

On first startup, it downloads and builds a SQLlite definitions.db file. This takes a while to download.

Use the EICAR test file for testing.

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