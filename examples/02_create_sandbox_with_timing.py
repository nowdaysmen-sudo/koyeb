#!/usr/bin/env python3
"""Create and manage a sandbox with detailed timing information for debugging"""

import os
import time
from datetime import datetime
from collections import defaultdict
try:
    from tqdm import tqdm
except ImportError:
    print("Warning: tqdm not installed. Install with: pip install tqdm")
    print("Continuing without progress bars...\n")
    tqdm = None


from koyeb import Sandbox


class TimingTracker:
    """Track timing information for operations"""
    def __init__(self):
        self.operations = []
        self.categories = defaultdict(list)
    
    def record(self, name, duration, category="general"):
        """Record an operation's timing"""
        self.operations.append({
            'name': name,
            'duration': duration,
            'category': category,
            'timestamp': datetime.now()
        })
        self.categories[category].append(duration)
    
    def get_total_time(self):
        """Get total time for all operations"""
        return sum(op['duration'] for op in self.operations)
    
    def get_category_total(self, category):
        """Get total time for a specific category"""
        return sum(self.categories[category])
    
    def print_recap(self):
        """Print a detailed recap of all timings"""
        print("\n" + "="*60)
        print("TIMING RECAP")
        print("="*60)
        
        if not self.operations:
            print("No operations recorded")
            return
        
        # Print individual operations
        print("\nIndividual Operations:")
        print("-" * 60)
        max_name_len = max(len(op['name']) for op in self.operations)
        
        for op in self.operations:
            bar_length = int(op['duration'] * 10)  # Scale for visualization
            bar = "█" * min(bar_length, 40)
            print(f"  {op['name']:<{max_name_len}} : {op['duration']:6.3f}s {bar}")
        
        # Print category summaries
        if len(self.categories) > 1:
            print("\nCategory Summaries:")
            print("-" * 60)
            for category, times in sorted(self.categories.items()):
                total = sum(times)
                count = len(times)
                avg = total / count if count > 0 else 0
                print(f"  {category.capitalize():<20} : {total:6.3f}s total, {avg:6.3f}s avg ({count} ops)")
        
        # Print total time with progress bar
        total_time = self.get_total_time()
        print("\n" + "-" * 60)
        print(f"  {'TOTAL TIME':<{max_name_len}} : {total_time:6.3f}s")
        print("="*60)


def log_with_timestamp(message, start_time=None):
    """Log a message with timestamp and optionally elapsed time"""
    current_time = datetime.now()
    timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    if start_time:
        elapsed = time.time() - start_time
        print(f"[{timestamp}] (+{elapsed:.3f}s) {message}")
    else:
        print(f"[{timestamp}] {message}")
    
    return time.time()


def main():
    script_start = time.time()
    tracker = TimingTracker()
    log_with_timestamp("=== Starting sandbox creation with timing debug ===")
    
    api_token = os.getenv("KOYEB_API_TOKEN")
    if not api_token:
        print("Error: KOYEB_API_TOKEN not set")
        return

    sandbox = None
    try:
        # Create sandbox with timing
        create_start = log_with_timestamp("Creating sandbox...")
        sandbox = Sandbox.create(
            image="python:3.11",
            name="example-sandbox-timed",
            wait_ready=True,
            api_token=api_token,
        )
        create_duration = time.time() - create_start
        tracker.record("Sandbox creation", create_duration, "setup")
        log_with_timestamp("Sandbox created successfully", create_start)

        # Check status with timing
        status_start = log_with_timestamp("Checking sandbox status...")
        status = sandbox.status()
        is_healthy = sandbox.is_healthy()
        status_duration = time.time() - status_start
        tracker.record("Status check", status_duration, "monitoring")
        log_with_timestamp(
            f"Status check complete - Status: {status}, Healthy: {is_healthy}",
            status_start
        )

        # Test command execution with timing
        exec_start = log_with_timestamp("Executing test command...")
        result = sandbox.exec("echo 'Sandbox is ready!'")
        exec_duration = time.time() - exec_start
        tracker.record("Initial exec command", exec_duration, "execution")
        log_with_timestamp(
            f"Command executed - Output: {result.stdout.strip()}",
            exec_start
        )

        # Additional timing tests
        log_with_timestamp("\n=== Running additional timing tests ===")
        
        # Test multiple commands
        test_range = range(3)
        iterator = tqdm(test_range, desc="Running test commands", unit="cmd") if tqdm else test_range
        
        for i in iterator:
            cmd_start = log_with_timestamp(f"Running command {i+1}/3...")
            result = sandbox.exec(f"echo 'Test {i+1}'")
            cmd_duration = time.time() - cmd_start
            tracker.record(f"Test command {i+1}", cmd_duration, "execution")
            log_with_timestamp(
                f"Command {i+1} completed - Output: {result.stdout.strip()}",
                cmd_start
            )

        # Test a longer-running command
        long_cmd_start = log_with_timestamp("Running longer command (sleep 2)...")
        
        # Show progress bar for long command if tqdm is available
        if tqdm:
            with tqdm(total=100, desc="Long command progress", bar_format='{l_bar}{bar}| {elapsed}') as pbar:
                for _ in range(10):
                    time.sleep(0.2)
                    pbar.update(10)
        result = sandbox.exec("sleep 2 && echo 'Done sleeping'")
        long_cmd_duration = time.time() - long_cmd_start
        tracker.record("Long command (sleep 2)", long_cmd_duration, "execution")
        log_with_timestamp(
            f"Long command completed - Output: {result.stdout.strip()}",
            long_cmd_start
        )

    except Exception as e:
        log_with_timestamp(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if sandbox:
            delete_start = log_with_timestamp("Deleting sandbox...")
            sandbox.delete()
            delete_duration = time.time() - delete_start
            tracker.record("Sandbox deletion", delete_duration, "cleanup")
            log_with_timestamp("Sandbox deleted successfully", delete_start)
        
        total_script_time = time.time() - script_start
        log_with_timestamp(
            f"\n=== Script completed ===",
            script_start
        )
        
        # Print detailed recap
        tracker.print_recap()


if __name__ == "__main__":
    main()
