import asyncio
import os
import sys
from typing import Dict, Optional, AsyncGenerator
from datetime import datetime
from mcp.server.fastmcp import FastMCP
import shlex
import subprocess
import random
import re
import json
import logging

# Initialize MCP server
mcp = FastMCP("terminal-controller")

from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)
    
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

LOG_FILE = "/tmp/terminal_controller.log"
DEFAULT_TIMEOUT = 300
SCREEN_SESSION = "terminal"

def wrap_stuff_command(cmd: str, safe=True) -> str:
    return cmd

CURRENT_USER = os.environ['HOME'].split('/')[-1]
CURRENT_HOST = os.environ['HOSTNAME']
TERMINATOR = f"{CURRENT_USER}@{CURRENT_HOST}"

from string import punctuation

async def random_batching(cmd: str, max_length: int = 10) -> AsyncGenerator[str, None]:
    it = 0
    
    while it < len(cmd):
        xx = random.randint(1, max_length)

        while it + xx < len(cmd) and cmd[it + xx - 1] in punctuation and cmd[it + xx] in punctuation:
            xx += 1

        yield cmd[it:it+xx]
        it += xx
        
def remove_console_color(text):
  """
  Removes ANSI color codes from a string.

  Args:
    text: The string to remove color codes from.

  Returns:
    The string with color codes removed.
  """
  return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)



async def type_command(cmd: str, fast=False) -> str:
    
    tokenized = []
    
    max_length = 10 if not fast else 30

    async for batch in random_batching(cmd, max_length=max_length):
        tokenized.append(batch)

    for i, c in enumerate(tokenized):
        subprocess.check_call(
            ["screen", "-S", SCREEN_SESSION, "-X", "stuff", c],
            stdout=sys.stderr,
            stderr=sys.stderr,
            env=os.environ,
        )

        await asyncio.sleep(random.uniform(0.04, 0.15 if not fast else 0.08))

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

            line = remove_console_color(line)
            output += line.replace(TERMINATOR, '') + '\n'

            if TERMINATOR in line:
                break

    return output

async def run_command(cmd: str, timeout: int = DEFAULT_TIMEOUT, safe=False, fast=False) -> Dict:
    """
    Execute command and return results
    
    Args:
        cmd: Command to execute
        timeout: Command timeout in seconds
        
    Returns:
        Dictionary containing command execution results
    """
    start_time = datetime.now()
    logger.info(f"Running command: {cmd}")

    try:
        await type_command(wrap_stuff_command(cmd, safe=safe), fast=fast)
        await flush_command()

        output = await capture_output()
        duration = datetime.now() - start_time

        result = AIResponse(
            success=True,
            output=output,
            duration=str(duration),
            command=cmd
        ).to_dict()

        return result
    
    except Exception as e:
        logger.error(f"Error running command '{cmd}': {e}")
        return AIResponse(
            success=False,
            output=str(e),
            return_code=-1,
            duration=str(datetime.now() - start_time),
            command=cmd
        ).to_dict()


@mcp.tool()
async def execute_command(command: str, filter_str: Optional[str] = None) -> str:
    """
    Execute command in a real terminal

    Args:
        command: Command line command to execute
        filter_str: Filter to apply to the command output
    
    Returns:
        Output of the command execution
    """

    if filter_str:
        quoted_filter_str = shlex.quote(filter_str)
        command += f" | grep {quoted_filter_str}"

    result = await run_command(command, safe=False)

    status = 'successfully' if result["success"] else 'failed'
    output = f"Command {status} executed\n\n"

    if result["output"]:
        output += f"Output:\n{result['output']}"

    return output

@mcp.tool()
async def get_command_history(count: int = 20, filter_str: Optional[str] = None) -> str:
    """
    Get recent command execution history
    
    Args:
        count: Number of recent commands to return
        filter_str: Filter to apply to the command output
    Returns:
        Formatted command history record
    """
    
    command = f"history {count}"
    
    if filter_str:
        quoted_filter_str = shlex.quote(filter_str)
        command += f" | grep {quoted_filter_str}"

    res = await run_command(command, safe=True)
    return res["output"]

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

    path = shlex.quote(path)
    res = await run_command(f"cd {path}", safe=True)
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

    # with open("test_"+path, 'w') as f:
    #     f.write(content)

    # quoted_content = shlex.quote(content).replace('$', r'\$').replace('\\"', r'\\"').replace('\\n', r'\\n')
    quoted_content = shlex.quote(content).replace('$', r'\$').replace('\\', r'\\')
    quoted_path = shlex.quote(path)

    if res["success"]:
        res = await run_command(
            f"echo {quoted_content} > {quoted_path}" 
            if file_mode == "w" else 
            f"echo {quoted_content} >> {quoted_path}",
            safe=True,
            fast=True
        )

        output += "\n" + res["output"]

    return output


@mcp.tool()
async def internet_search(query: str) -> str:
    """
    Search the general related information on the internet

    Args:
        query: Query to search for

    Returns: Related information
    """

    body = {
        "url": "https://api.tavily.com/search",
        "headers": {
            "Content-Type": "application/json",
        },
        "body": {
            "query": query,
            "max_results": 10,
            "include_image_descriptions": True,
            "include_images": True,
            "topic": "general"
        },
        "method": "POST"
    }

    body_str = json.dumps(body)
    
    data = {
        'messages': [
            {
                'role': 'user',
                'content': body_str
            }
        ]
    }

    data_str = shlex.quote(json.dumps(data, indent=2)).replace('$', "'$'").replace('\\"', r'\\"')
    command = f"curl -X POST \$ETERNALAI_MCP_PROXY_URL -H 'Content-Type: application/json' -d {data_str}"
    res = await run_command(command, safe=True, fast=True)
    return res["output"]


@mcp.tool()
async def news_search(query: str) -> str:
    """
    Search the related latest news on the internet

    Args:
        query: Query to search for

    Returns: Related latest news
    """

    body = {
        "url": "https://api.tavily.com/search",
        "headers": {
            "Content-Type": "application/json",
        },
        "body": {
            "query": query,
            "max_results": 10,
            "include_image_descriptions": True,
            "include_images": True,
            "days": 7,
            "topic": "news"
        },
        "method": "POST"
    }

    body_str = json.dumps(body)
    
    data = {
        'messages': [
            {
                'role': 'user',
                'content': body_str
            }
        ]
    }

    data_str = shlex.quote(json.dumps(data, indent=2)).replace('$', "'$'").replace('\\"', r'\\"')
    command = f"curl -X POST \$ETERNALAI_MCP_PROXY_URL -H 'Content-Type: application/json' -d {data_str}"
    res = await run_command(command, safe=True, fast=True)
    return res["output"]


async def fetch(url: str, filter_str: Optional[str] = None) -> str:
    """
    Fetch the content from the given URL
    
    Args:
        url: URL to fetch content from
        filter_str: Filter to apply to the content

    Returns: Content from the URL
    """
    
    command = f"curl -s '{url}'"
    
    if filter_str:
        quoted_filter_str = shlex.quote(filter_str)
        command += f" | grep {quoted_filter_str}"

    res = await run_command(command, safe=True, fast=True)
    return res["output"]


def main():
    """
    Entry point function that runs the MCP server.
    """
    print("Starting Terminal Controller MCP Server...", file=sys.stderr)

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

        subprocess.check_call(
            ["screen", "-S", SCREEN_SESSION, "-X", "stuff", "history -c && clear\n"],
            stdout=sys.stderr,
            stderr=sys.stderr,
            env=os.environ,
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
        print(f"Exception raised: {e}", file=sys.stderr)
    finally:
        if process:
            process.terminate()

if __name__ == "__main__":
    main()