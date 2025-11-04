#!/usr/bin/env python3
"""Background process management (async variant)"""

import asyncio
import os

from koyeb import AsyncSandbox


async def main():
    api_token = os.getenv("KOYEB_API_TOKEN")
    if not api_token:
        print("Error: KOYEB_API_TOKEN not set")
        return

    sandbox = None
    try:
        sandbox = await AsyncSandbox.create(
            image="koyeb/sandbox",
            name="background-processes",
            wait_ready=True,
            api_token=api_token,
        )

        print("Launching background processes...")

        # Launch a long-running process
        process_id_1 = await sandbox.launch_process(
            "python3 -c 'import time; [print(f\"Process 1: {i}\") or time.sleep(1) for i in range(10)]'"
        )
        print(f"Launched process 1: {process_id_1}")

        # Launch another process with a different command
        process_id_2 = await sandbox.launch_process(
            "python3 -c 'import time; [print(f\"Process 2: {i}\") or time.sleep(1) for i in range(5)]'"
        )
        print(f"Launched process 2: {process_id_2}")

        # Wait a bit for processes to start
        await asyncio.sleep(2)

        # List all processes
        print("\nListing all processes:")
        processes = await sandbox.list_processes()
        for process in processes:
            print(f"  ID: {process.get('id', 'N/A')}")
            print(f"  Status: {process.get('status', 'N/A')}")
            if process.get("pid"):
                print(f"  PID: {process.get('pid')}")
            print()

        # Kill a specific process
        print(f"Killing process {process_id_2}...")
        await sandbox.kill_process(process_id_2)
        print("Process killed")

        # Wait a bit
        await asyncio.sleep(1)

        # List processes again
        print("\nListing processes after kill:")
        processes = await sandbox.list_processes()
        for process in processes:
            print(f"  ID: {process.get('id', 'N/A')}")
            print(f"  Status: {process.get('status', 'N/A')}")
            print()

        # Launch a few more processes
        process_id_3 = await sandbox.launch_process("sleep 5")
        process_id_4 = await sandbox.launch_process("sleep 5")
        print(f"Launched processes 3 and 4: {process_id_3}, {process_id_4}")

        # Wait a bit
        await asyncio.sleep(1)

        # Kill all running processes
        print("\nKilling all running processes...")
        killed_count = await sandbox.kill_all_processes()
        print(f"Killed {killed_count} processes")

        # Final list
        print("\nFinal process list:")
        processes = await sandbox.list_processes()
        for process in processes:
            print(f"  ID: {process.get('id', 'N/A')}")
            print(f"  Status: {process.get('status', 'N/A')}")
            print()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if sandbox:
            await sandbox.delete()


if __name__ == "__main__":
    asyncio.run(main())
