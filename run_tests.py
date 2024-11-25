import os
import time
import subprocess
import matplotlib.pyplot as plt
import numpy as np

def run_scan(folder, num_threads):

    return time.time() - start_time

def benchmark_folder(folder_path):
    results = {}
    max_threads = os.cpu_count()
    
    for threads in range(1, max_threads + 1):
        print(f"Testing {folder_path} with {threads} threads...")
        start_time = time.time()
        result = subprocess.run(
            ['python', 'main.py', '--num_threads', str(threads), folder_path],
            capture_output=True,
            text=True
        )
        results[threads] = time.time() - start_time
    
    return results

def main():
    tests_dir = 'tests'
    if not os.path.exists(tests_dir):
        print("Test files do not exist.")
        return

    all_results = {}
    
    for folder in os.listdir(tests_dir):
        folder_path = os.path.join(tests_dir, folder)
        if os.path.isdir(folder_path):
            print(f"\nBenchmarking {folder}...")
            results = benchmark_folder(folder_path)
            all_results[folder] = results
            
            print(f"\nResults for {folder}:")
            for threads, time_taken in results.items():
                print(f"Threads: {threads}, Time: {time_taken:.2f}s")
    
        plt.figure(figsize=(12, 8))
    
    colors = plt.cm.rainbow(np.linspace(0, 1, len(all_results)))
    
    for (folder_name, results), color in zip(all_results.items(), colors):
        threads = list(results.keys())
        times = list(results.values())
        plt.plot(threads, times, 'o-', label=folder_name, color=color)
    
    plt.title('Scan Performance Comparison')
    plt.xlabel('Number of Threads')
    plt.ylabel('Time (seconds)')
    plt.grid(True)
    plt.legend()
    plt.savefig('benchmark_comparison.png')
    plt.close()

if __name__ == "__main__":
    main()