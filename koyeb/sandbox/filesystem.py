# coding: utf-8

"""
Filesystem operations for Koyeb Sandbox instances
Using only the primitives available in the Koyeb API
"""

import asyncio
import base64
import os
import shlex
from dataclasses import dataclass
from typing import Dict, List, Union

from .exec import _exec_async
from .utils import SandboxError, ensure_sandbox_healthy


class SandboxFilesystemError(SandboxError):
    """Base exception for filesystem operations"""


class FileNotFoundError(SandboxFilesystemError):
    """Raised when file or directory not found"""


class FileExistsError(SandboxFilesystemError):
    """Raised when file already exists"""


@dataclass
class FileInfo:
    """File information"""

    content: str
    encoding: str


class SandboxFilesystem:
    """
    Synchronous filesystem operations for Koyeb Sandbox instances.
    Using only the primitives available in the Koyeb API.
    
    For async usage, use AsyncSandboxFilesystem instead.
    """

    def __init__(self, sandbox):
        self.sandbox = sandbox

    def write_file(
        self, path: str, content: Union[str, bytes], encoding: str = "utf-8"
    ) -> None:
        """
        Write content to a file synchronously.

        Args:
            path: Absolute path to the file
            content: Content to write (string or bytes)
            encoding: File encoding (default: "utf-8"). Use "base64" for binary data.
        """
        asyncio.run(self._write_file_async(path, content, encoding))

    async def _write_file_async(
        self, path: str, content: Union[str, bytes], encoding: str = "utf-8"
    ) -> None:
        """Internal async implementation for write_file"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)

        escaped_path = shlex.quote(path)

        if isinstance(content, bytes):
            content_str = content.decode("utf-8", errors="replace")
        else:
            content_str = content

        if encoding == "base64":
            content_b64 = content_str
        else:
            content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")

        escaped_b64 = shlex.quote(content_b64)

        result = await _exec_async(
            instance_id=self.sandbox.instance_id,
            command=f"printf '%s' {escaped_b64} | base64 -d > {escaped_path}",
            api_token=self.sandbox.api_token,
            sandbox_secret=self.sandbox.sandbox_secret,
        )

        if not result.success:
            if "Permission denied" in result.stderr:
                raise SandboxFilesystemError(f"Permission denied: {path}")
            raise SandboxFilesystemError(f"Failed to write file: {result.stderr}")

    def read_file(self, path: str, encoding: str = "utf-8") -> FileInfo:
        """
        Read a file from the sandbox synchronously.

        Args:
            path: Absolute path to the file
            encoding: File encoding (default: "utf-8"). Use "base64" for binary data.

        Returns:
            FileInfo: Object with content and encoding
        """
        return asyncio.run(self._read_file_async(path, encoding))

    async def _read_file_async(self, path: str, encoding: str = "utf-8") -> FileInfo:
        """Internal async implementation for read_file"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)

        escaped_path = shlex.quote(path)

        if encoding == "base64":
            result = await _exec_async(
                instance_id=self.sandbox.instance_id,
                command=f"base64 < {escaped_path}",
                api_token=self.sandbox.api_token,
                sandbox_secret=self.sandbox.sandbox_secret,
            )
        else:
            result = await _exec_async(
                instance_id=self.sandbox.instance_id,
                command=f"cat {escaped_path}",
                api_token=self.sandbox.api_token,
                sandbox_secret=self.sandbox.sandbox_secret,
            )

        if not result.success:
            if "No such file or directory" in result.stderr:
                raise FileNotFoundError(f"File not found: {path}")
            if "Permission denied" in result.stderr:
                raise SandboxFilesystemError(f"Permission denied: {path}")
            raise SandboxFilesystemError(f"Failed to read file: {result.stderr}")

        return FileInfo(content=result.stdout.strip(), encoding=encoding)

    def mkdir(self, path: str, recursive: bool = False) -> None:
        """
        Create a directory synchronously.

        Args:
            path: Absolute path to the directory
            recursive: Create parent directories if needed (default: False)
        """
        asyncio.run(self._mkdir_async(path, recursive))

    async def _mkdir_async(self, path: str, recursive: bool = False) -> None:
        """Internal async implementation for mkdir"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)

        if recursive:
            result = await _exec_async(
                instance_id=self.sandbox.instance_id,
                command=["mkdir", "-p", path],
                api_token=self.sandbox.api_token,
                sandbox_secret=self.sandbox.sandbox_secret,
            )
        else:
            result = await _exec_async(
                instance_id=self.sandbox.instance_id,
                command=["mkdir", path],
                api_token=self.sandbox.api_token,
                sandbox_secret=self.sandbox.sandbox_secret,
            )

        if not result.success:
            if "File exists" in result.stderr:
                raise FileExistsError(f"Directory already exists: {path}")
            if "Permission denied" in result.stderr:
                raise SandboxFilesystemError(f"Permission denied: {path}")
            raise SandboxFilesystemError(f"Failed to create directory: {result.stderr}")

    def list_dir(self, path: str = ".") -> List[str]:
        """
        List contents of a directory synchronously.

        Args:
            path: Path to the directory (default: current directory)

        Returns:
            List[str]: Names of files and directories within the specified path.
        """
        return asyncio.run(self._list_dir_async(path))

    async def _list_dir_async(self, path: str = ".") -> List[str]:
        """Internal async implementation for list_dir"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)

        result = await _exec_async(
            instance_id=self.sandbox.instance_id,
            command=["ls", "-A", path],
            api_token=self.sandbox.api_token,
            sandbox_secret=self.sandbox.sandbox_secret,
        )

        if not result.success:
            if "No such file or directory" in result.stderr:
                raise FileNotFoundError(f"Directory not found: {path}")
            if "Permission denied" in result.stderr:
                raise SandboxFilesystemError(f"Permission denied: {path}")
            raise SandboxFilesystemError(f"Failed to list directory: {result.stderr}")

        return [item for item in result.stdout.splitlines() if item]

    def delete_file(self, path: str) -> None:
        """
        Delete a file synchronously.

        Args:
            path: Absolute path to the file
        """
        asyncio.run(self._delete_file_async(path))

    async def _delete_file_async(self, path: str) -> None:
        """Internal async implementation for delete_file"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)

        result = await _exec_async(
            instance_id=self.sandbox.instance_id,
            command=["rm", path],
            api_token=self.sandbox.api_token,
            sandbox_secret=self.sandbox.sandbox_secret,
        )

        if not result.success:
            if "No such file or directory" in result.stderr:
                raise FileNotFoundError(f"File not found: {path}")
            if "Permission denied" in result.stderr:
                raise SandboxFilesystemError(f"Permission denied: {path}")
            raise SandboxFilesystemError(f"Failed to delete file: {result.stderr}")

    def delete_dir(self, path: str) -> None:
        """
        Delete a directory synchronously.

        Args:
            path: Absolute path to the directory
        """
        asyncio.run(self._delete_dir_async(path))

    async def _delete_dir_async(self, path: str) -> None:
        """Internal async implementation for delete_dir"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)

        result = await _exec_async(
            instance_id=self.sandbox.instance_id,
            command=["rmdir", path],
            api_token=self.sandbox.api_token,
            sandbox_secret=self.sandbox.sandbox_secret,
        )

        if not result.success:
            if "No such file or directory" in result.stderr:
                raise FileNotFoundError(f"Directory not found: {path}")
            if "Directory not empty" in result.stderr:
                raise SandboxFilesystemError(f"Directory not empty: {path}")
            if "Permission denied" in result.stderr:
                raise SandboxFilesystemError(f"Permission denied: {path}")
            raise SandboxFilesystemError(f"Failed to delete directory: {result.stderr}")

    def rename_file(self, old_path: str, new_path: str) -> None:
        """
        Rename a file synchronously.

        Args:
            old_path: Current file path
            new_path: New file path
        """
        asyncio.run(self._rename_file_async(old_path, new_path))

    async def _rename_file_async(self, old_path: str, new_path: str) -> None:
        """Internal async implementation for rename_file"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)

        result = await _exec_async(
            instance_id=self.sandbox.instance_id,
            command=["mv", old_path, new_path],
            api_token=self.sandbox.api_token,
            sandbox_secret=self.sandbox.sandbox_secret,
        )

        if not result.success:
            if "No such file or directory" in result.stderr:
                raise FileNotFoundError(f"File not found: {old_path}")
            if "Permission denied" in result.stderr:
                raise SandboxFilesystemError(f"Permission denied: {old_path}")
            raise SandboxFilesystemError(f"Failed to rename file: {result.stderr}")

    def move_file(self, source_path: str, destination_path: str) -> None:
        """
        Move a file to a different directory synchronously.

        Args:
            source_path: Current file path
            destination_path: Destination path
        """
        asyncio.run(self._move_file_async(source_path, destination_path))

    async def _move_file_async(self, source_path: str, destination_path: str) -> None:
        """Internal async implementation for move_file"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)

        result = await _exec_async(
            instance_id=self.sandbox.instance_id,
            command=["mv", source_path, destination_path],
            api_token=self.sandbox.api_token,
            sandbox_secret=self.sandbox.sandbox_secret,
        )

        if not result.success:
            if "No such file or directory" in result.stderr:
                raise FileNotFoundError(f"File not found: {source_path}")
            if "Permission denied" in result.stderr:
                raise SandboxFilesystemError(f"Permission denied: {source_path}")
            raise SandboxFilesystemError(f"Failed to move file: {result.stderr}")

    def write_files(self, files: List[Dict[str, str]]) -> None:
        """
        Write multiple files in a single operation synchronously.

        Args:
            files: List of dictionaries, each with 'path', 'content', and optional 'encoding'.
        """
        for file_info in files:
            path = file_info["path"]
            content = file_info["content"]
            encoding = file_info.get("encoding", "utf-8")
            self.write_file(path, content, encoding)

    def exists(self, path: str) -> bool:
        """Check if file/directory exists synchronously"""
        return asyncio.run(self._exists_async(path))

    async def _exists_async(self, path: str) -> bool:
        """Internal async implementation for exists"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)
        result = await _exec_async(
            instance_id=self.sandbox.instance_id,
            command=["test", "-e", path],
            api_token=self.sandbox.api_token,
            sandbox_secret=self.sandbox.sandbox_secret,
        )
        return result.success

    def is_file(self, path: str) -> bool:
        """Check if path is a file synchronously"""
        return asyncio.run(self._is_file_async(path))

    async def _is_file_async(self, path: str) -> bool:
        """Internal async implementation for is_file"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)
        result = await _exec_async(
            instance_id=self.sandbox.instance_id,
            command=["test", "-f", path],
            api_token=self.sandbox.api_token,
            sandbox_secret=self.sandbox.sandbox_secret,
        )
        return result.success

    def is_dir(self, path: str) -> bool:
        """Check if path is a directory synchronously"""
        return asyncio.run(self._is_dir_async(path))

    async def _is_dir_async(self, path: str) -> bool:
        """Internal async implementation for is_dir"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)
        result = await _exec_async(
            instance_id=self.sandbox.instance_id,
            command=["test", "-d", path],
            api_token=self.sandbox.api_token,
            sandbox_secret=self.sandbox.sandbox_secret,
        )
        return result.success

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """
        Upload a local file to the sandbox synchronously.

        Args:
            local_path: Path to the local file
            remote_path: Destination path in the sandbox
        """
        asyncio.run(self._upload_file_async(local_path, remote_path))

    async def _upload_file_async(self, local_path: str, remote_path: str) -> None:
        """Internal async implementation for upload_file"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)

        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")

        with open(local_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        await self._write_file_async(remote_path, content, encoding="base64")

    def download_file(self, remote_path: str, local_path: str) -> None:
        """
        Download a file from the sandbox to a local path synchronously.

        Args:
            remote_path: Path to the file in the sandbox
            local_path: Destination path on the local filesystem
        """
        asyncio.run(self._download_file_async(remote_path, local_path))

    async def _download_file_async(self, remote_path: str, local_path: str) -> None:
        """Internal async implementation for download_file"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)

        file_info = await self._read_file_async(remote_path, encoding="base64")
        content = base64.b64decode(file_info.content)

        with open(local_path, "wb") as f:
            f.write(content)

    def ls(self, path: str = ".") -> List[str]:
        """
        List directory contents synchronously.

        Args:
            path: Path to list

        Returns:
            List of file/directory names
        """
        return self.list_dir(path)

    def rm(self, path: str, recursive: bool = False) -> None:
        """
        Remove file or directory synchronously.

        Args:
            path: Path to remove
            recursive: Remove recursively
        """
        asyncio.run(self._rm_async(path, recursive))

    async def _rm_async(self, path: str, recursive: bool = False) -> None:
        """Internal async implementation for rm"""
        ensure_sandbox_healthy(self.sandbox.instance_id, self.sandbox.api_token)

        if recursive:
            result = await _exec_async(
                instance_id=self.sandbox.instance_id,
                command=["rm", "-rf", path],
                api_token=self.sandbox.api_token,
            )
        else:
            result = await _exec_async(
                instance_id=self.sandbox.instance_id,
                command=["rm", path],
                api_token=self.sandbox.api_token,
            )

        if not result.success:
            if "No such file or directory" in result.stderr:
                raise FileNotFoundError(f"File not found: {path}")
            raise SandboxFilesystemError(f"Failed to remove: {result.stderr}")

    def open(self, path: str, mode: str = "r") -> "SandboxFileIO":
        """
        Open a file in the sandbox synchronously.

        Args:
            path: Path to the file
            mode: Open mode ('r', 'w', 'a', etc.)

        Returns:
            SandboxFileIO: File handle
        """
        return SandboxFileIO(self, path, mode)


class AsyncSandboxFilesystem(SandboxFilesystem):
    """
    Async filesystem operations for Koyeb Sandbox instances.
    Inherits from SandboxFilesystem and provides async methods.
    """

    async def write_file(
        self, path: str, content: Union[str, bytes], encoding: str = "utf-8"
    ) -> None:
        """
        Write content to a file asynchronously.

        Args:
            path: Absolute path to the file
            content: Content to write (string or bytes)
            encoding: File encoding (default: "utf-8"). Use "base64" for binary data.
        """
        await self._write_file_async(path, content, encoding)

    async def read_file(self, path: str, encoding: str = "utf-8") -> FileInfo:
        """
        Read a file from the sandbox asynchronously.

        Args:
            path: Absolute path to the file
            encoding: File encoding (default: "utf-8"). Use "base64" for binary data.

        Returns:
            FileInfo: Object with content and encoding
        """
        return await self._read_file_async(path, encoding)

    async def mkdir(self, path: str, recursive: bool = False) -> None:
        """
        Create a directory asynchronously.

        Args:
            path: Absolute path to the directory
            recursive: Create parent directories if needed (default: False)
        """
        await self._mkdir_async(path, recursive)

    async def list_dir(self, path: str = ".") -> List[str]:
        """
        List contents of a directory asynchronously.

        Args:
            path: Path to the directory (default: current directory)

        Returns:
            List[str]: Names of files and directories within the specified path.
        """
        return await self._list_dir_async(path)

    async def delete_file(self, path: str) -> None:
        """
        Delete a file asynchronously.

        Args:
            path: Absolute path to the file
        """
        await self._delete_file_async(path)

    async def delete_dir(self, path: str) -> None:
        """
        Delete a directory asynchronously.

        Args:
            path: Absolute path to the directory
        """
        await self._delete_dir_async(path)

    async def rename_file(self, old_path: str, new_path: str) -> None:
        """
        Rename a file asynchronously.

        Args:
            old_path: Current file path
            new_path: New file path
        """
        await self._rename_file_async(old_path, new_path)

    async def move_file(self, source_path: str, destination_path: str) -> None:
        """
        Move a file to a different directory asynchronously.

        Args:
            source_path: Current file path
            destination_path: Destination path
        """
        await self._move_file_async(source_path, destination_path)

    async def write_files(self, files: List[Dict[str, str]]) -> None:
        """
        Write multiple files in a single operation asynchronously.

        Args:
            files: List of dictionaries, each with 'path', 'content', and optional 'encoding'.
        """
        for file_info in files:
            path = file_info["path"]
            content = file_info["content"]
            encoding = file_info.get("encoding", "utf-8")
            await self.write_file(path, content, encoding)

    async def exists(self, path: str) -> bool:
        """Check if file/directory exists asynchronously"""
        return await self._exists_async(path)

    async def is_file(self, path: str) -> bool:
        """Check if path is a file asynchronously"""
        return await self._is_file_async(path)

    async def is_dir(self, path: str) -> bool:
        """Check if path is a directory asynchronously"""
        return await self._is_dir_async(path)

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """
        Upload a local file to the sandbox asynchronously.

        Args:
            local_path: Path to the local file
            remote_path: Destination path in the sandbox
        """
        await self._upload_file_async(local_path, remote_path)

    async def download_file(self, remote_path: str, local_path: str) -> None:
        """
        Download a file from the sandbox to a local path asynchronously.

        Args:
            remote_path: Path to the file in the sandbox
            local_path: Destination path on the local filesystem
        """
        await self._download_file_async(remote_path, local_path)

    async def ls(self, path: str = ".") -> List[str]:
        """
        List directory contents asynchronously.

        Args:
            path: Path to list

        Returns:
            List of file/directory names
        """
        return await self.list_dir(path)

    async def rm(self, path: str, recursive: bool = False) -> None:
        """
        Remove file or directory asynchronously.

        Args:
            path: Path to remove
            recursive: Remove recursively
        """
        await self._rm_async(path, recursive)

    def open(self, path: str, mode: str = "r") -> "AsyncSandboxFileIO":
        """
        Open a file in the sandbox asynchronously.

        Args:
            path: Path to the file
            mode: Open mode ('r', 'w', 'a', etc.)

        Returns:
            AsyncSandboxFileIO: Async file handle
        """
        return AsyncSandboxFileIO(self, path, mode)


class SandboxFileIO:
    """Synchronous file I/O handle for sandbox files"""

    def __init__(self, filesystem: SandboxFilesystem, path: str, mode: str):
        self.filesystem = filesystem
        self.path = path
        self.mode = mode
        self._closed = False

    def read(self) -> str:
        """Read file content synchronously"""
        if "r" not in self.mode:
            raise ValueError("File not opened for reading")

        if self._closed:
            raise ValueError("File is closed")

        file_info = self.filesystem.read_file(self.path)
        return file_info.content

    def write(self, content: str) -> None:
        """Write content to file synchronously"""
        if "w" not in self.mode and "a" not in self.mode:
            raise ValueError("File not opened for writing")

        if self._closed:
            raise ValueError("File is closed")

        if "a" in self.mode:
            try:
                existing = self.filesystem.read_file(self.path)
                content = existing.content + content
            except FileNotFoundError:
                pass

        self.filesystem.write_file(self.path, content)

    def close(self) -> None:
        """Close the file"""
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class AsyncSandboxFileIO:
    """Async file I/O handle for sandbox files"""

    def __init__(self, filesystem: AsyncSandboxFilesystem, path: str, mode: str):
        self.filesystem = filesystem
        self.path = path
        self.mode = mode
        self._closed = False

    async def read(self) -> str:
        """Read file content asynchronously"""
        if "r" not in self.mode:
            raise ValueError("File not opened for reading")

        if self._closed:
            raise ValueError("File is closed")

        file_info = await self.filesystem.read_file(self.path)
        return file_info.content

    async def write(self, content: str) -> None:
        """Write content to file asynchronously"""
        if "w" not in self.mode and "a" not in self.mode:
            raise ValueError("File not opened for writing")

        if self._closed:
            raise ValueError("File is closed")

        if "a" in self.mode:
            try:
                existing = await self.filesystem.read_file(self.path)
                content = existing.content + content
            except FileNotFoundError:
                pass

        await self.filesystem.write_file(self.path, content)

    def close(self) -> None:
        """Close the file"""
        self._closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()
