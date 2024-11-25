import os
import random

def create_random_file(file_path, size_in_mb):
    with open(file_path, 'wb') as f:
        f.write(os.urandom(size_in_mb * 1024 * 1024))

def create_test_folders(base_path, test_cases):
    if not os.path.exists(base_path):
        os.makedirs(base_path)

    for count, size in test_cases:
        folder_name = f"{count}_{size}M"
        folder_path = os.path.join(base_path, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        for i in range(count):
            file_name = f"file_{i+1}.bin"
            file_path = os.path.join(folder_path, file_name)
            create_random_file(file_path, size)

if __name__ == "__main__":
    base_path = "tests"
    test_cases = [
        (5000, 1),
        (2500, 2),
        (500, 10),
        (200, 25),
        (100, 50),
        (50, 100),
        (5, 1000),
        (1, 5000)
    ]
    create_test_folders(base_path, test_cases)