# ParallelVirusScanner

Install Dependencies with pip
```
pip install -r requirements.txt
```

On first startup, it downloads and builds a SQLlite definitions.db file. This takes a while to download.

Use the EICAR test file for testing.

```sh
python main.py [-h] [--num_threads NUM_THREADS] [--mode {all,md5}] [--verbose] [--bypass_checks] path

positional arguments:
  path                  Path to the file or directory to scan

options:
  -h, --help                show this help message and exit
  --num_threads NUM_THREADS Number of threads
  --mode {all,md5,zip}      Scan Mode
  --verbose                 Set verbose mode
  --bypass_checks           Bypasses validation checks
```