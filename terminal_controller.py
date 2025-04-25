import asyncio
import os
import platform
import sys
from typing import List, Dict, Optional, Union
from datetime import datetime
from tokenize import tokenize
from mcp.server.fastmcp import FastMCP
import json
import shlex
import subprocess
import random
from typing import AsyncGenerator
import re
# Initialize MCP server
mcp = FastMCP("terminal-controller")

from dataclasses import dataclass, field
    
@dataclass
class AIResponse:
    success: bool = field(default=False)
    output: str = field(default='')
    return_code: int = field(default=-1)
    duration: str = field(default='')
    command: str = field(default='')
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "return_code": self.return_code,
            "duration": self.duration,
            "command": self.command
        }

@dataclass
class CommandHistory:
    timestamp: str = field(default='')
    command: str = field(default='')
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "command": self.command
        }
    
    def __repr__(self) -> str:
        return str(self.to_dict())
    
    def __str__(self) -> str:
        return str(self.to_dict())

# List to store command history
command_history: List[CommandHistory] = []

# Maximum history size
MAX_HISTORY_SIZE = 50
LOG_FILE = "/tmp/terminal_controller.log"
DONE_TOKEN = "[__COMMAND_COMPLETED__]"
DEFAULT_TIMEOUT = 300
AGENT_SH = "/bin/agent.sh"
SCREEN_SESSION = "terminal"

def wrap_stuff_command(cmd: str, safe=True) -> str:
    return cmd

CURRENT_USER = os.environ['HOME'].split('/')[-1]
CURRENT_HOST = os.environ['HOSTNAME']
TERMINATOR = f"{CURRENT_USER}@{CURRENT_HOST}"

async def random_batching(cmd: str) -> AsyncGenerator[str, None]:
    it = 0
    
    while it < len(cmd):
        xx = random.randint(1, 10)
        yield cmd[it:it+xx]
        it += xx
        
        
def remove_console_colors(output: str) -> str:
    return re.sub(r'\x1b\[[0-9;]*m', '', output)

async def type_command(cmd: str) -> str:

    tokenized = []
    
    async for batch in random_batching(cmd):
        tokenized.append(batch)
    
    for i, c in enumerate(tokenized):
        subprocess.check_call(
            ["screen", "-S", SCREEN_SESSION, "-X", "stuff", c],
            stdout=sys.stderr,
            stderr=sys.stderr,
            env=os.environ,
        )

        await asyncio.sleep(random.uniform(0.05, 0.15))

async def flush_command() -> str:
    # clear the log file before flushing
    with open(LOG_FILE, 'w') as f:
        f.write('')

    subprocess.check_call(["screen", "-S", SCREEN_SESSION, "-X", "stuff", '\n'])
    
async def flush_log() -> str:
    subprocess.check_call(["screen", "-S", SCREEN_SESSION, "-X", "colon", "logfile flush 1^M"])

async def capture_output() -> str:
    output = ''

    with open(LOG_FILE, 'r') as f:
        f.seek(0, 2)

        while True:
            line = f.readline()

            if not line:
                await asyncio.sleep(.3)
                # await flush_log()
                continue

            line = remove_console_colors(line)
            output += line.replace(TERMINATOR, '') + '\n'

            if TERMINATOR in line:
                break

    return output

async def run_command(cmd: str, timeout: int = DEFAULT_TIMEOUT, safe=False) -> Dict:
    """
    Execute command and return results
    
    Args:
        cmd: Command to execute
        timeout: Command timeout in seconds
        
    Returns:
        Dictionary containing command execution results
    """
    start_time = datetime.now()

    try:
        await type_command(wrap_stuff_command(cmd, safe=safe))
        await flush_command()

        output = await capture_output()
        duration = datetime.now() - start_time

        result = AIResponse(
            success=True,
            output=output,
            duration=str(duration),
            command=cmd
        ).to_dict()
        
        # Add to history
        command_history.append(
            CommandHistory(
                timestamp=datetime.now().isoformat(),
                command=cmd
            ).to_dict()
        )

        # If history is too long, remove oldest record
        if len(command_history) > MAX_HISTORY_SIZE:
            command_history.pop(0)

        return result
    
    except Exception as e:
        return AIResponse(
            success=False,
            output=str(e),
            return_code=-1,
            duration=str(datetime.now() - start_time),
            command=cmd
        ).to_dict()


@mcp.tool()
async def execute_command(command: str) -> str:
    """
    Execute command in a real terminal

    Args:
        command: Command line command to execute
    
    Returns:
        Output of the command execution
    """

    result = await run_command(command, safe=False)

    status = 'successfully' if result["success"] else 'failed'
    output = f"Command {status} executed\n\n"

    if result["output"]:
        output += f"Output:\n{result['output']}"

    return output

@mcp.tool()
async def get_command_history(count: int = 10) -> str:
    """
    Get recent command execution history
    
    Args:
        count: Number of recent commands to return
    
    Returns:
        Formatted command history record
    """
    if not command_history:
        return "No command execution history."
    
    count = min(count, len(command_history))
    recent_commands = command_history[-count:]
    
    output = f"Recent {count} command history:\n\n"
    
    for i, cmd in enumerate(recent_commands):
        cmd: CommandHistory
        output += f"{i+1}. {cmd.timestamp}: {cmd.command}\n"
    
    return output

@mcp.tool()
async def get_current_directory() -> str:
    """
    Get current working directory
    
    Returns:
        Path of current working directory
    """

    res = await run_command("pwd", safe=True)
    return res["output"]

@mcp.tool()
async def change_directory(path: str) -> str:
    """
    Change current working directory
    
    Args:
        path: Directory path to switch to
    
    Returns:
        Operation result information
    """

    path = path.strip('" \t\n\r')
    res = await run_command(f"cd {path!r}", safe=True)
    return res["output"]

@mcp.tool()
async def list_directory(path: Optional[str] = None) -> str:
    """
    List files and subdirectories in the specified directory
    
    Args:
        path: Directory path to list contents, default is current directory
    
    Returns:
        List of directory contents
    """

    if path:
        path = path.strip('" \t\n\r')
    else:
        path = '.'

    quoted_path = shlex.quote(path)
    res = await run_command(f"ls -la {quoted_path}", safe=True)
    return res["output"]

def quote_content(content: str) -> str:
    return content.replace("'", "\\'")

@mcp.tool()
async def write_file(path: str, content: str, mode: str = "overwrite") -> str:
    """
    Write content to a file
    
    Args:
        path: Path to the file
        content: Content to write (string or JSON object)
        mode: Write mode ('overwrite' or 'append')
    
    Returns:
        Operation result information
    """
    
    output = ''
    
    file_mode = "w" if mode.lower() == "overwrite" else "a"
    directory = os.path.dirname(os.path.abspath(path))
    
    res = {
        "success": os.path.exists(directory),
    }

    if not os.path.exists(directory):
        quoted_dir = shlex.quote(directory)
        res = await run_command(f"mkdir -p {quoted_dir}", safe=True)
        output += res["output"]

    if content and not content.endswith('\n'):
        content += '\n'

    quoted_content = shlex.quote(content).replace('$', r'\$')
    quoted_path = shlex.quote(path)

    if res["success"]:
        res = await run_command(
            f"echo {quoted_content} > {quoted_path}" 
            if file_mode == "w" else 
            f"echo {quoted_content} >> {quoted_path}",
            safe=True
        )

        output += "\n" + res["output"]

    # if res["success"]:
    #     res = await run_command(f"du -sh {quoted_path}", safe=False)
    #     output += "\n" + res["output"]

    return output

def beautify_json(json_data: Union[Dict, List, str]) -> dict:
    if isinstance(json_data, dict):
        return {
            k: beautify_json(v) 
            for k, v in json_data.items()
        }
    elif isinstance(json_data, list):
        return [beautify_json(item) for item in json_data]
    elif isinstance(json_data, str):
        try:
            e = json.loads(json_data)
            return beautify_json(e)
        except Exception as e:
            return json_data
    else:
        return json_data


def main():
    """
    Entry point function that runs the MCP server.
    """
    print("Starting Terminal Controller MCP Server...", file=sys.stderr)

    import subprocess

    process = None

    try:
        with open(os.path.expanduser('~/.screenrc'), 'a') as f:
            f.write('termcapinfo xterm* ti@:te@\n')

        with open(os.path.expanduser('~/.bashrc'), 'a') as f:
            f.write('export TERM=xterm-256color\n')

        subprocess.check_call(
            ["screen", "-dmS", SCREEN_SESSION, "-s", "bash"],
            stdout=sys.stderr,
            stderr=sys.stderr,
            env=os.environ
        )

        process = subprocess.Popen(
            ["ttyd", "-p", "7681", "--writable", "screen", "-x", SCREEN_SESSION],
            stdout=sys.stderr,
            stderr=sys.stderr,
            env=os.environ,
        )

        subprocess.check_call(
            ["screen", "-S", SCREEN_SESSION, "-X", "logfile", LOG_FILE],
            stdout=sys.stderr,
            stderr=sys.stderr,
            env=os.environ,
        )

        subprocess.check_call(
            ["screen", "-S", SCREEN_SESSION, "-X", "log", "on"],
            stdout=sys.stderr,
            stderr=sys.stderr,
            env=os.environ,
        )
        
        subprocess.check_call(
            ["screen", "-S", SCREEN_SESSION, "-X", "deflog", "on"],
            stdout=sys.stderr,
            stderr=sys.stderr,
            env=os.environ,
        )
        
        subprocess.check_call(
            ["screen", "-S", SCREEN_SESSION, "-X", "logfile", "flush", "1"],
            stdout=sys.stderr,
            stderr=sys.stderr,
            env=os.environ,
        )

        mcp.run(transport='stdio')
    except Exception as e:
        print(f"Error starting ttyd: {e}", file=sys.stderr)
        return
    finally:
        if process:
            process.terminate()

if __name__ == "__main__":
    main()