# coding: utf-8

"""
Command execution utilities for Koyeb Sandbox instances
Using WebSocket connection to Koyeb API
"""

import asyncio
import base64
import json
import shlex
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional, Union

import websockets

from koyeb.api.models.stream_result_of_exec_command_reply import (
    StreamResultOfExecCommandReply,
)

from .utils import SandboxError, get_api_client


class CommandStatus(str, Enum):
    """Command execution status"""

    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


@dataclass
class CommandResult:
    """Result of a command execution using Koyeb API models"""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    status: CommandStatus = CommandStatus.FINISHED
    duration: float = 0.0
    command: str = ""
    args: Optional[List[str]] = None

    def __post_init__(self):
        if self.args is None:
            self.args = []

    @property
    def success(self) -> bool:
        """Check if command executed successfully"""
        return self.exit_code == 0 and self.status == CommandStatus.FINISHED

    @property
    def output(self) -> str:
        """Get combined stdout and stderr output"""
        return self.stdout + (f"\n{self.stderr}" if self.stderr else "")


class SandboxCommandError(SandboxError):
    """Raised when command execution fails"""


class SandboxExecutor:
    """
    Synchronous command execution interface for Koyeb Sandbox instances.
    Bound to a specific sandbox instance.
    
    For async usage, use AsyncSandboxExecutor instead.
    """

    def __init__(self, sandbox):
        self.sandbox = sandbox

    def __call__(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """
        Execute a command in a shell synchronously. Supports streaming output via callbacks.

        Args:
            command: Command to execute as a string (e.g., "python -c 'print(2+2)'")
            cwd: Working directory for the command
            env: Environment variables for the command
            timeout: Command timeout in seconds
            on_stdout: Optional callback for streaming stdout chunks
            on_stderr: Optional callback for streaming stderr chunks

        Returns:
            CommandResult: Result of the command execution

        Example:
            ```python
            # Synchronous execution
            result = sandbox.exec("echo hello")

            # With streaming callbacks
            result = sandbox.exec(
                "echo hello; sleep 1; echo world",
                on_stdout=lambda data: print(f"OUT: {data}"),
                on_stderr=lambda data: print(f"ERR: {data}"),
            )
            ```
        """
        return asyncio.run(
            _exec_async(
                instance_id=self.sandbox.instance_id,
                command=command,
                cwd=cwd,
                env=env,
                timeout=timeout,
                api_token=self.sandbox.api_token,
                sandbox_secret=self.sandbox.sandbox_secret,
                on_stdout=on_stdout,
                on_stderr=on_stderr,
            )
        )


class AsyncSandboxExecutor(SandboxExecutor):
    """
    Async command execution interface for Koyeb Sandbox instances.
    Bound to a specific sandbox instance.
    
    Inherits from SandboxExecutor and provides async command execution.
    """

    async def __call__(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """
        Execute a command in a shell asynchronously. Supports streaming output via callbacks.

        Args:
            command: Command to execute as a string (e.g., "python -c 'print(2+2)'")
            cwd: Working directory for the command
            env: Environment variables for the command
            timeout: Command timeout in seconds
            on_stdout: Optional callback for streaming stdout chunks
            on_stderr: Optional callback for streaming stderr chunks

        Returns:
            CommandResult: Result of the command execution

        Example:
            ```python
            # Async execution
            result = await sandbox.exec("echo hello")

            # With streaming callbacks
            result = await sandbox.exec(
                "echo hello; sleep 1; echo world",
                on_stdout=lambda data: print(f"OUT: {data}"),
                on_stderr=lambda data: print(f"ERR: {data}"),
            )
            ```
        """
        return await _exec_async(
            instance_id=self.sandbox.instance_id,
            command=command,
            cwd=cwd,
            env=env,
            timeout=timeout,
            api_token=self.sandbox.api_token,
            sandbox_secret=self.sandbox.sandbox_secret,
            on_stdout=on_stdout,
            on_stderr=on_stderr,
        )


def _normalize_command(command: Union[str, List[str]], *args: str) -> str:
    """Normalize command to a string, handling both string and list formats"""
    if isinstance(command, str):
        if args:
            # Join command and args with proper quoting
            return (
                shlex.quote(command) + " " + " ".join(shlex.quote(arg) for arg in args)
            )
        return command
    else:
        # List of commands - join them for shell execution
        all_args = list(command) + list(args)
        return " ".join(shlex.quote(arg) for arg in all_args)


def _build_shell_command(
    command: Union[str, List[str]],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Build a shell command with environment variables and working directory"""
    # If command is a string, use it as-is
    if isinstance(command, str):
        shell_cmd = command
    else:
        # If it's a list, join it as a shell command
        shell_cmd = " ".join(shlex.quote(arg) for arg in command)

    # Build the full command with env and cwd
    parts = []

    if cwd:
        parts.append(f"cd {shlex.quote(cwd)}")

    if env:
        env_vars = []
        for key, value in env.items():
            escaped_key = shlex.quote(key)
            escaped_value = shlex.quote(value)
            env_vars.append(f"{escaped_key}={escaped_value}")
        if env_vars:
            shell_cmd = " ".join(env_vars) + " " + shell_cmd

    if parts:
        shell_cmd = " && ".join(parts) + " && " + shell_cmd

    return ["sh", "-c", shell_cmd]


def _decode_base64_content(content: Union[str, bytes]) -> str:
    """Safely decode base64 content with proper error handling"""
    if isinstance(content, str):
        try:
            return base64.b64decode(content).decode("utf-8")
        except (base64.binascii.Error, UnicodeDecodeError):
            # If base64 decoding fails, return as-is (might be plain text)
            return content
    else:
        return content.decode("utf-8")


def _process_websocket_message(
    message: str,
) -> tuple[Optional[str], Optional[str], Optional[int], Optional[str], bool]:
    """Process WebSocket message using SDK models

    Returns:
        tuple: (stdout, stderr, exit_code, error, is_finished)
    """
    try:
        stream_result = StreamResultOfExecCommandReply.from_dict(json.loads(message))
    except (json.JSONDecodeError, ValueError) as e:
        return None, None, None, f"Failed to parse WebSocket message: {e}", False

    if stream_result.result:
        result = stream_result.result
        stdout = ""
        stderr = ""
        exit_code = None
        is_finished = False

        if result.stdout and result.stdout.data:
            stdout = _decode_base64_content(result.stdout.data)

        if result.stderr and result.stderr.data:
            stderr = _decode_base64_content(result.stderr.data)

        if result.exit_code is not None:
            exit_code = result.exit_code
            # Only mark as finished if exited flag is explicitly set
            # Otherwise, we might get exit_code but still have more output
            if hasattr(result, "exited") and result.exited:
                is_finished = True
            # If exit_code is set but exited is not, don't mark as finished yet
            # to allow for more output chunks

        return stdout, stderr, exit_code, None, is_finished

    elif stream_result.error:
        error_msg = stream_result.error.message or "Unknown error"
        return None, None, None, f"API Error: {error_msg}", True

    return None, None, None, None, False


def _get_websocket_url_and_headers(
    instance_id: str, api_token: Optional[str] = None
) -> tuple[str, Dict[str, str]]:
    """
    Get WebSocket URL and headers using SDK API client configuration.

    Args:
        instance_id: The instance ID
        api_token: API token (if None, will use get_api_client which reads from env)

    Returns:
        Tuple of (websocket_url, headers_dict)
    """
    _, _, instances_api = get_api_client(api_token)
    api_client = instances_api.api_client
    config = api_client.configuration

    host = config.host.replace("https://", "wss://").replace("http://", "ws://")
    ws_url = f"{host}/v1/streams/instances/exec?id={instance_id}"

    headers = {}
    auth_token = config.get_api_key_with_prefix("Bearer")
    if auth_token:
        headers["Authorization"] = auth_token

    return ws_url, headers


async def _execute_websocket_command(
    instance_id: str,
    command: List[str],
    api_token: Optional[str] = None,
    input_data: Optional[str] = None,
    timeout: int = 30,
    on_stdout: Optional[Callable[[str], None]] = None,
    on_stderr: Optional[Callable[[str], None]] = None,
) -> CommandResult:
    """Execute a command via WebSocket with proper timeout handling"""
    start_time = time.time()

    ws_url, headers = _get_websocket_url_and_headers(instance_id, api_token)

    _, _, instances_api = get_api_client(api_token)
    api_token_for_subprotocol = instances_api.api_client.configuration.api_key.get(
        "Bearer"
    )

    try:
        async with asyncio.timeout(timeout):
            async with websockets.connect(
                ws_url,
                additional_headers=headers,
                subprotocols=(
                    ["Bearer", api_token_for_subprotocol]
                    if api_token_for_subprotocol
                    else None
                ),
            ) as websocket:
                command_frame = {
                    "id": instance_id,
                    "body": {"command": command},
                }
                await websocket.send(json.dumps(command_frame))

                if input_data:
                    input_frame = {
                        "id": instance_id,
                        "body": {
                            "stdin": {
                                "data": base64.b64encode(
                                    input_data.encode("utf-8")
                                ).decode("utf-8"),
                                "close": True,
                            }
                        },
                    }
                    await websocket.send(json.dumps(input_frame))

                stdout_data = []
                stderr_data = []
                exit_code = 0

                async for message in websocket:
                    stdout, stderr, cmd_exit_code, error, is_finished = (
                        _process_websocket_message(message)
                    )

                    if error:
                        stderr_data.append(error)
                        if on_stderr:
                            on_stderr(error)
                        if "API Error" in error:
                            exit_code = 1
                            break
                        continue

                    # Process stdout first (may come with exit_code in same message)
                    if stdout:
                        stdout_data.append(stdout)
                        if on_stdout:
                            on_stdout(stdout)

                    # Process stderr first (may come with exit_code in same message)
                    if stderr:
                        stderr_data.append(stderr)
                        if on_stderr:
                            on_stderr(stderr)

                    # Store exit code but don't break yet - there might be more output
                    if cmd_exit_code is not None:
                        exit_code = cmd_exit_code

                    # Only break when explicitly finished - continue processing until all output is received
                    if is_finished:
                        break
                    # If we have exit code but websocket closes naturally, that's fine too

                return CommandResult(
                    stdout="".join(stdout_data),
                    stderr="".join(stderr_data),
                    exit_code=exit_code,
                    status=(
                        CommandStatus.FINISHED
                        if exit_code == 0
                        else CommandStatus.FAILED
                    ),
                    duration=time.time() - start_time,
                    command=command[0] if command else "",
                    args=command[1:] if len(command) > 1 else [],
                )

    except asyncio.TimeoutError:
        return CommandResult(
            stdout="",
            stderr=f"Command timed out after {timeout} seconds",
            exit_code=1,
            status=CommandStatus.FAILED,
            duration=time.time() - start_time,
            command=command[0] if command else "",
            args=command[1:] if len(command) > 1 else [],
        )
    except Exception as e:
        return CommandResult(
            stdout="",
            stderr=f"Command execution failed: {str(e)}",
            exit_code=1,
            status=CommandStatus.FAILED,
            duration=time.time() - start_time,
            command=command[0] if command else "",
            args=command[1:] if len(command) > 1 else [],
        )


async def _exec_async(
    instance_id: str,
    command: Union[str, List[str]],
    *args: str,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    api_token: Optional[str] = None,
    sandbox_secret: Optional[str] = None,
    on_stdout: Optional[Callable[[str], None]] = None,
    on_stderr: Optional[Callable[[str], None]] = None,
) -> CommandResult:
    """
    Execute a command in a shell via WebSocket connection to Koyeb API.

    Internal function - use sandbox.exec() for the public API. This function handles
    command normalization and delegates to the WebSocket execution handler.

    Supports streaming output via on_stdout/on_stderr callbacks.
    """
    full_cmd = _normalize_command(command, *args)
    
    # Merge sandbox_secret into environment if provided
    exec_env = env.copy() if env else {}
    if sandbox_secret:
        exec_env["SANDBOX_SECRET"] = sandbox_secret
    
    shell_command = _build_shell_command(full_cmd, cwd, exec_env)

    return await _execute_websocket_command(
        instance_id=instance_id,
        command=shell_command,
        api_token=api_token,
        timeout=timeout,
        on_stdout=on_stdout,
        on_stderr=on_stderr,
    )
