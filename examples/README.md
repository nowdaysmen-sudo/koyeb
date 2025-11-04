# Koyeb Sandbox Examples

A collection of examples demonstrating the Koyeb Sandbox SDK capabilities.

## Quick Start

```bash
# Set your API token
export KOYEB_API_TOKEN=your_api_token_here

# Run individual examples
uv run python examples/01_create_sandbox.py
```

## Examples

- **01_create_sandbox.py** - Create and manage sandbox instances
- **02_basic_commands.py** - Basic command execution
- **03_streaming_output.py** - Real-time streaming output
- **04_environment_variables.py** - Environment variable configuration
- **05_working_directory.py** - Working directory management
- **06_file_operations.py** - File read/write operations
- **07_directory_operations.py** - Directory management
- **08_binary_files.py** - Binary file handling
- **09_batch_operations.py** - Batch file operations
- **10_upload_download.py** - File upload and download
- **11_file_manipulation.py** - File manipulation operations

## Basic Usage

```python
from koyeb import Sandbox

# Create a sandbox
sandbox = await Sandbox.create(
    image="koyeb/sandbox",
    name="my-sandbox",
    wait_ready=True,
    api_token=api_token,
)

# Execute commands
result = await sandbox.exec("echo 'Hello World'")
print(result.stdout)

# Use filesystem
await sandbox.filesystem.write_file("/tmp/file.txt", "Hello!")
content = await sandbox.filesystem.read_file("/tmp/file.txt")

# Cleanup
await sandbox.delete()
```

## Prerequisites

- Koyeb API token from https://app.koyeb.com/account/api
- Python 3.9+
- `uv` package manager (or `pip`)
