import os
import time
import subprocess
import matplotlib.pyplot as plt
import numpy as np
import re

def benchmark_folder(folder_path):
    results = {'block': {}, 'cycle': {}}
    max_threads = os.cpu_count()
    
    for scheduling in ['block', 'cycle']:
        for threads in range(1, max_threads + 1):
            print(f"Testing {folder_path} with {threads} threads using {scheduling} scheduling...")
            start_time = time.time()
            result = subprocess.run(
                ['python', 'main.py', 
                 '--num_threads', str(threads),
                 '--scheduling', scheduling,
                 folder_path],
                capture_output=True,
                text=True
            )
            results[scheduling][threads] = time.time() - start_time
    
    return results

def main():
    tests_dir = 'tests'
    if not os.path.exists(tests_dir):
        print("Test files do not exist.")
        return

    all_results = {}
    
    for folder in os.listdir(tests_dir):
        folder_path = os.path.join(tests_dir, folder)
        if os.path.isdir(folder_path) and re.match('\\d{,4}_\\d{,4}M', folder) is not None:
            print(f"\nBenchmarking {folder}...")
            results = benchmark_folder(folder_path)
            all_results[folder] = results
            
            print(f"\nResults for {folder}:")
            for scheduling, scheduling_results in results.items():
                print(f"Scheduling: {scheduling}")
                for threads, time_taken in scheduling_results.items():
                    print(f"Threads: {threads}, Time: {time_taken:.2f}s")
    
        plt.figure(figsize=(12, 8))
    
    colors = plt.cm.rainbow(np.linspace(0, 1, len(all_results)))
    
    for (folder_name, results), color in zip(all_results.items(), colors):
        for scheduling, scheduling_results in results.items():
            threads = list(scheduling_results.keys())
            times = list(scheduling_results.values())
            plt.plot(threads, times, 'o-', label=f"{folder_name} ({scheduling})", color=color)
    
    plt.title('Scan Performance Comparison')
    plt.xlabel('Number of Threads')
    plt.ylabel('Time (seconds)')
    plt.grid(True)
    plt.legend()
    plt.savefig('benchmark_comparison.png')
    plt.close()

if __name__ == "__main__":
    main()
