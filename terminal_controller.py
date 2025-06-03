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

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
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
    OUTPUT_LENGTH_LIMIT = 40000
    output = []

    with open(LOG_FILE, 'rb') as f:
        f.seek(0, 2)

        while True:
            line = f.readline()

            if not line:
                await asyncio.sleep(.3)
                # await flush_log()
                continue

            line = line.decode('utf-8', errors='replace')
            line = remove_console_color(line)
            output.append(line.replace(TERMINATOR, ''))

            if TERMINATOR in line:
                break

    total_length = 0
    start_index = 0
    for i in range(len(output)-1, -1, -1):        
        start_index = i
        total_length += len(output[i])
        if total_length > OUTPUT_LENGTH_LIMIT:
            break

    return '\n'.join(output[start_index:])


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


# @mcp.tool()
# async def get_weather(location_code: str) -> str:
#     """
#     Get weather information for a given location

#     Args:
#         location_code: 3-letter airport code of the location to get weather for
    
#     Returns:
#         Weather information for the given location
#     """

#     location_code = shlex.quote(location_code)

#     command = f"curl wttr.in/{location_code}"

#     result = await run_command(command, safe=False)
    
#     return result["output"]


# @mcp.tool()
# async def get_crypto_market_info() -> str:
#     """
#     Get information for the overall crypto market

#     Returns:
#         Information for the overall crypto market
#     """

#     command = f"curl rate.sx"

#     result = await run_command(command, safe=False)
    
#     return result["output"]


# @mcp.tool()
# async def get_cryptocoin_info(symbol: str) -> str:
#     """
#     Get information for a given crypto coin

#     Args:
#         symbol: Symbol of the crypto coin to get information for
    
#     Returns:
#         Information for the given crypto coin
#     """

#     symbol = shlex.quote(symbol.lower())

#     command = f"curl rate.sx/{symbol}"

#     result = await run_command(command, safe=False)
    
#     return result["output"]


# @mcp.tool()
# async def get_joke(query: Optional[str] = None, limit: Optional[int] = 1) -> str:
#     """
#     Get a random joke

#     Args:
#         query: Query to search for
#         limit: Number of jokes to return

#     Returns:
#         A random joke
#     """

#     url = f"https://icanhazdadjoke.com/search?limit={limit}"
#     if query:
#         url += f"&term={shlex.quote(query)}"

#     command = f'curl -H "Accept: text/plain" "{url}" | cowsay | lolcat'

#     result = await run_command(command, safe=False)
    
#     return result["output"]


# @mcp.tool()
# async def display_parrot() -> str:
#     """
#     Display a parrot
#     """
    
#     command = f'curl parrot.live'
    
#     result = await run_command(command, safe=False)

#     return "Oh wait there's actually a parrot here"
    
#     # return result["output"]


# @mcp.tool()
# async def ping_website(url: str) -> str:
#     """
#     Ping a website

#     Args:
#         url: URL of the website to ping. Only include the domain name, without the protocol.

#     Returns:
#         Result of the ping
#     """
    
#     command = f'prettyping {url}'

#     result = await run_command(command, safe=False)
    
#     return result["output"]


# @mcp.tool()
# async def get_command_history(count: int = 20, filter_str: Optional[str] = None) -> str:
#     """
#     Get recent command execution history
    
#     Args:
#         count: Number of recent commands to return
#         filter_str: Filter to apply to the command output
#     Returns:
#         Formatted command history record
#     """
    
#     command = f"history {count}"
    
#     if filter_str:
#         quoted_filter_str = shlex.quote(filter_str)
#         command += f" | grep {quoted_filter_str}"

#     res = await run_command(command, safe=True)
#     return res["output"]

# @mcp.tool()
# async def get_current_directory() -> str:
#     """
#     Get current working directory
    
#     Returns:
#         Path of current working directory
#     """

#     res = await run_command("pwd", safe=True)
#     return res["output"]

# @mcp.tool()
# async def change_directory(path: str) -> str:
#     """
#     Change current working directory
    
#     Args:
#         path: Directory path to switch to
    
#     Returns:
#         Operation result information
#     """

#     path = shlex.quote(path)
#     res = await run_command(f"cd {path}", safe=True)
#     return res["output"]

# @mcp.tool()
# async def list_directory(path: Optional[str] = None) -> str:
#     """
#     List files and subdirectories in the specified directory
    
#     Args:
#         path: Directory path to list contents, default is current directory
    
#     Returns:
#         List of directory contents
#     """

#     if path:
#         path = path.strip('" \t\n\r')
#     else:
#         path = '.'

#     quoted_path = shlex.quote(path)
#     res = await run_command(f"ls -la {quoted_path}", safe=True)
#     return res["output"]

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

    quoted_content = shlex.quote(
        content if isinstance(content, str) else json.dumps(content)
    ).replace('$', r'\$').replace('\\', r'\\')

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

    with open(path, file_mode, encoding='utf-8') as f:
        if isinstance(content, str):
            f.write(content)
        else:
            try:
                import json
                json.dump(content, f, indent=4, sort_keys=False, ensure_ascii=False)
            except Exception as e:
                pass

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
            "max_results": 5,
            "include_image_descriptions": True,
            "include_images": True,
            "search_depth": "advanced",
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

    # proxy_url = os.environ.get('ETERNALAI_MCP_PROXY_URL', 'undefined')

    # session = requests.Session()
    # request = requests.Request('POST', proxy_url, json=data, headers={'Content-Type': 'application/json'})
    # prepared = session.prepare_request(request)
    # command = curlify.to_curl(prepared)

    # with open("test_internet_search.json", "w") as f:
    #     f.write(data_str)

    data_str = json.dumps(data, indent=2)
    data_str = shlex.quote(data_str).replace('\\', r'\\')
    command = f"curl -X POST \\$ETERNALAI_MCP_PROXY_URL -H 'Content-Type: application/json' -d {data_str}"
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
            "max_results": 5,
            "include_image_descriptions": True,
            "include_images": True,
            "days": 7,
            "search_depth": "advanced",
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


    # proxy_url = os.environ.get('ETERNALAI_MCP_PROXY_URL', 'undefined')

    # session = requests.Session()
    # request = requests.Request('POST', proxy_url, json=data, headers={'Content-Type': 'application/json'})
    # prepared = session.prepare_request(request)
    # command = curlify.to_curl(prepared)

    data_str = json.dumps(data, indent=2)
    data_str = shlex.quote(data_str).replace('\\', r'\\')
    command = f"curl -X POST \\$ETERNALAI_MCP_PROXY_URL -H 'Content-Type: application/json' -d {data_str}"
    res = await run_command(command, safe=True, fast=True)
    return res["output"]


# @mcp.tool()
# async def read_file(path: str, start_row: int = None, end_row: int = None, as_json: bool = False) -> str:
#     """
#     Read content from a file with optional row selection
    
#     Args:
#         path: Path to the file
#         start_row: Starting row to read from (0-based, optional)
#         end_row: Ending row to read to (0-based, inclusive, optional)
#         as_json: If True, attempt to parse file content as JSON (optional)
    
#     Returns:
#         File content or selected lines, optionally parsed as JSON
#     """
#     try:
#         if not os.path.exists(path):
#             return f"Error: File '{path}' does not exist."
            
#         if not os.path.isfile(path):
#             return f"Error: '{path}' is not a file."
        
#         # Check file size before reading to prevent memory issues
#         file_size = os.path.getsize(path)
#         if file_size > 10 * 1024 * 1024:  # 10 MB limit
#             return f"Warning: File is very large ({file_size/1024/1024:.2f} MB). Consider using row selection."
            
#         with open(path, 'r', encoding='utf-8', errors='replace') as file:
#             lines = file.readlines()
            
#         # If row selection is specified
#         if start_row is not None:
#             if start_row < 0:
#                 return "Error: start_row must be non-negative."
                
#             # If only start_row is specified, read just that single row
#             if end_row is None:
#                 if start_row >= len(lines):
#                     return f"Error: start_row {start_row} is out of range (file has {len(lines)} lines)."
#                 content = f"Line {start_row}: {lines[start_row]}"
#             else:
#                 # Both start_row and end_row are specified
#                 if end_row < start_row:
#                     return "Error: end_row must be greater than or equal to start_row."
                    
#                 if end_row >= len(lines):
#                     end_row = len(lines) - 1
                    
#                 selected_lines = lines[start_row:end_row+1]
#                 content = ""
#                 for i, line in enumerate(selected_lines):
#                     content += f"Line {start_row + i}: {line}" if not line.endswith('\n') else f"Line {start_row + i}: {line}"
#         else:
#             # If no row selection, return the entire file
#             content = "".join(lines)
        
#         # If as_json is True, try to parse the content as JSON
#         if as_json:
#             try:
#                 import json
#                 # If we're showing line numbers, we cannot parse as JSON
#                 if start_row is not None:
#                     return "Error: Cannot parse as JSON when displaying line numbers. Use as_json without row selection."
                
#                 # Try to parse the content as JSON
#                 parsed_json = json.loads(content)
#                 # Return pretty-printed JSON for better readability
#                 return json.dumps(parsed_json, indent=4, sort_keys=False, ensure_ascii=False)
#             except json.JSONDecodeError as e:
#                 return f"Error: File content is not valid JSON. {str(e)}\n\nRaw content:\n{content}"
        
#         return content
            
#     except PermissionError:
#         return f"Error: No permission to read file '{path}'."
#     except Exception as e:
#         return f"Error reading file: {str(e)}"

# @mcp.tool()
# async def insert_file_content(path: str, content: str, row: int = None, rows: list = None) -> str:
#     """
#     Insert content at specific row(s) in a file
    
#     Args:
#         path: Path to the file
#         content: Content to insert (string or JSON object)
#         row: Row number to insert at (0-based, optional)
#         rows: List of row numbers to insert at (0-based, optional)
    
#     Returns:
#         Operation result information
#     """
#     try:
#         # Handle different content types
#         if not isinstance(content, str):
#             try:
#                 import json
#                 content = json.dumps(content, indent=4, sort_keys=False, ensure_ascii=False, default=str)
#             except Exception as e:
#                 return f"Error: Unable to convert content to JSON string: {str(e)}"
            
#         # Ensure content ends with a newline if it doesn't already
#         if content and not content.endswith('\n'):
#             content += '\n'
            
#         # Create file if it doesn't exist
#         directory = os.path.dirname(os.path.abspath(path))
#         if not os.path.exists(directory):
#             os.makedirs(directory, exist_ok=True)
            
#         if not os.path.exists(path):
#             with open(path, 'w', encoding='utf-8') as file:
#                 pass
            
#         with open(path, 'r', encoding='utf-8', errors='replace') as file:
#             lines = file.readlines()
        
#         # Ensure all existing lines end with newlines
#         for i in range(len(lines)):
#             if lines[i] and not lines[i].endswith('\n'):
#                 lines[i] += '\n'
        
#         # Prepare lines for insertion
#         content_lines = content.splitlines(True)  # Keep line endings
        
#         # Handle inserting at specific rows
#         if rows is not None:
#             if not isinstance(rows, list):
#                 return "Error: 'rows' parameter must be a list of integers."
                
#             # Sort rows in descending order to avoid changing indices during insertion
#             rows = sorted(rows, reverse=True)
            
#             for r in rows:
#                 if not isinstance(r, int) or r < 0:
#                     return "Error: Row numbers must be non-negative integers."
                    
#                 if r > len(lines):
#                     # If row is beyond the file, append necessary empty lines
#                     lines.extend(['\n'] * (r - len(lines)))
#                     lines.extend(content_lines)
#                 else:
#                     # Insert content at each specified row
#                     for line in reversed(content_lines):
#                         lines.insert(r, line)
            
#             # Write back to the file
#             with open(path, 'w', encoding='utf-8') as file:
#                 file.writelines(lines)
                
#             return f"Successfully inserted content at rows {rows} in '{path}'."
            
#         # Handle inserting at a single row
#         elif row is not None:
#             if not isinstance(row, int) or row < 0:
#                 return "Error: Row number must be a non-negative integer."
                
#             if row > len(lines):
#                 # If row is beyond the file, append necessary empty lines
#                 lines.extend(['\n'] * (row - len(lines)))
#                 lines.extend(content_lines)
#             else:
#                 # Insert content at the specified row
#                 for line in reversed(content_lines):
#                     lines.insert(row, line)
            
#             # Write back to the file
#             with open(path, 'w', encoding='utf-8') as file:
#                 file.writelines(lines)
                
#             return f"Successfully inserted content at row {row} in '{path}'."
        
#         # If neither row nor rows specified, append to the end
#         else:
#             with open(path, 'a', encoding='utf-8') as file:
#                 file.write(content)
#             return f"Successfully appended content to '{path}'."
            
#     except PermissionError:
#         return f"Error: No permission to modify file '{path}'."
#     except Exception as e:
#         return f"Error inserting content: {str(e)}"

# @mcp.tool()
# async def delete_file_content(path: str, row: int = None, rows: list = None, substring: str = None) -> str:
#     """
#     Delete content at specific row(s) from a file
    
#     Args:
#         path: Path to the file
#         row: Row number to delete (0-based, optional)
#         rows: List of row numbers to delete (0-based, optional)
#         substring: If provided, only delete this substring within the specified row(s), not the entire row (optional)
    
#     Returns:
#         Operation result information
#     """
#     try:
#         if not os.path.exists(path):
#             return f"Error: File '{path}' does not exist."
            
#         if not os.path.isfile(path):
#             return f"Error: '{path}' is not a file."
            
#         with open(path, 'r', encoding='utf-8', errors='replace') as file:
#             lines = file.readlines()
        
#         total_lines = len(lines)
#         deleted_rows = []
#         modified_rows = []
        
#         # Handle substring deletion (doesn't delete entire rows)
#         if substring is not None:
#             # For multiple rows
#             if rows is not None:
#                 if not isinstance(rows, list):
#                     return "Error: 'rows' parameter must be a list of integers."
                
#                 for r in rows:
#                     if not isinstance(r, int) or r < 0:
#                         return "Error: Row numbers must be non-negative integers."
                        
#                     if r < total_lines and substring in lines[r]:
#                         original_line = lines[r]
#                         lines[r] = lines[r].replace(substring, '')
#                         # Ensure line ends with newline if original did
#                         if original_line.endswith('\n') and not lines[r].endswith('\n'):
#                             lines[r] += '\n'
#                         modified_rows.append(r)
            
#             # For single row
#             elif row is not None:
#                 if not isinstance(row, int) or row < 0:
#                     return "Error: Row number must be a non-negative integer."
                    
#                 if row >= total_lines:
#                     return f"Error: Row {row} is out of range (file has {total_lines} lines)."
                    
#                 if substring in lines[row]:
#                     original_line = lines[row]
#                     lines[row] = lines[row].replace(substring, '')
#                     # Ensure line ends with newline if original did
#                     if original_line.endswith('\n') and not lines[row].endswith('\n'):
#                         lines[row] += '\n'
#                     modified_rows.append(row)
            
#             # For entire file
#             else:
#                 for i in range(len(lines)):
#                     if substring in lines[i]:
#                         original_line = lines[i]
#                         lines[i] = lines[i].replace(substring, '')
#                         # Ensure line ends with newline if original did
#                         if original_line.endswith('\n') and not lines[i].endswith('\n'):
#                             lines[i] += '\n'
#                         modified_rows.append(i)
            
#             # Write back to the file
#             with open(path, 'w', encoding='utf-8') as file:
#                 file.writelines(lines)
                
#             if not modified_rows:
#                 return f"No occurrences of '{substring}' found in the specified rows."
#             return f"Successfully removed '{substring}' from {len(modified_rows)} rows ({modified_rows}) in '{path}'."
        
#         # Handle deleting multiple rows
#         elif rows is not None:
#             if not isinstance(rows, list):
#                 return "Error: 'rows' parameter must be a list of integers."
                
#             # Sort rows in descending order to avoid changing indices during deletion
#             rows = sorted(rows, reverse=True)
            
#             for r in rows:
#                 if not isinstance(r, int) or r < 0:
#                     return "Error: Row numbers must be non-negative integers."
                    
#                 if r < total_lines:
#                     lines.pop(r)
#                     deleted_rows.append(r)
            
#             # Write back to the file
#             with open(path, 'w', encoding='utf-8') as file:
#                 file.writelines(lines)
                
#             if not deleted_rows:
#                 return f"No rows were within range to delete (file has {total_lines} lines)."
#             return f"Successfully deleted {len(deleted_rows)} rows ({deleted_rows}) from '{path}'."
            
#         # Handle deleting a single row
#         elif row is not None:
#             if not isinstance(row, int) or row < 0:
#                 return "Error: Row number must be a non-negative integer."
                
#             if row >= total_lines:
#                 return f"Error: Row {row} is out of range (file has {total_lines} lines)."
                
#             # Delete the specified row
#             lines.pop(row)
            
#             # Write back to the file
#             with open(path, 'w', encoding='utf-8') as file:
#                 file.writelines(lines)
                
#             return f"Successfully deleted row {row} from '{path}'."
        
#         # If neither row nor rows specified, clear the file
#         else:
#             with open(path, 'w', encoding='utf-8') as file:
#                 pass
#             return f"Successfully cleared all content from '{path}'."
            
#     except PermissionError:
#         return f"Error: No permission to modify file '{path}'."
#     except Exception as e:
#         return f"Error deleting content: {str(e)}"

# @mcp.tool()
# async def update_file_content(path: str, content: str, row: int = None, rows: list = None, substring: str = None) -> str:
#     """
#     Update content at specific row(s) in a file
    
#     Args:
#         path: Path to the file
#         content: New content to place at the specified row(s)
#         row: Row number to update (0-based, optional)
#         rows: List of row numbers to update (0-based, optional)
#         substring: If provided, only replace this substring within the specified row(s), not the entire row
    
#     Returns:
#         Operation result information
#     """
#     try:
#         # Handle different content types
#         if not isinstance(content, str):
#             try:
#                 import json
#                 content = json.dumps(content, indent=4, sort_keys=False, ensure_ascii=False, default=str)
#             except Exception as e:
#                 return f"Error: Unable to convert content to JSON string: {str(e)}"
        
#         if not os.path.exists(path):
#             return f"Error: File '{path}' does not exist."
            
#         if not os.path.isfile(path):
#             return f"Error: '{path}' is not a file."
            
#         with open(path, 'r', encoding='utf-8', errors='replace') as file:
#             lines = file.readlines()
        
#         total_lines = len(lines)
#         updated_rows = []
        
#         # Ensure content ends with a newline if replacing a full line and doesn't already have one
#         if substring is None and content and not content.endswith('\n'):
#             content += '\n'
        
#         # Prepare lines for update
#         content_lines = content.splitlines(True) if substring is None else [content]
        
#         # Handle updating multiple rows
#         if rows is not None:
#             if not isinstance(rows, list):
#                 return "Error: 'rows' parameter must be a list of integers."
                
#             for r in rows:
#                 if not isinstance(r, int) or r < 0:
#                     return "Error: Row numbers must be non-negative integers."
                    
#                 if r < total_lines:
#                     # If substring is provided, only replace that part
#                     if substring is not None:
#                         # Only update if substring exists in the line
#                         if substring in lines[r]:
#                             original_line = lines[r]
#                             lines[r] = lines[r].replace(substring, content)
#                             # Ensure line ends with newline if original did
#                             if original_line.endswith('\n') and not lines[r].endswith('\n'):
#                                 lines[r] += '\n'
#                             updated_rows.append(r)
#                     else:
#                         # Otherwise, replace the entire line
#                         # If we have multiple content lines, use them in sequence
#                         if len(content_lines) > 1:
#                             content_index = r % len(content_lines)
#                             lines[r] = content_lines[content_index]
#                         else:
#                             # If we have only one content line, use it for all rows
#                             lines[r] = content_lines[0] if content_lines else "\n"
#                         updated_rows.append(r)
            
#             # Write back to the file
#             with open(path, 'w', encoding='utf-8') as file:
#                 file.writelines(lines)
                
#             if not updated_rows:
#                 if substring is not None:
#                     return f"No occurrences of substring '{substring}' found in the specified rows (file has {total_lines} lines)."
#                 else:
#                     return f"No rows were within range to update (file has {total_lines} lines)."
            
#             if substring is not None:
#                 return f"Successfully updated substring in {len(updated_rows)} rows ({updated_rows}) in '{path}'."
#             else:
#                 return f"Successfully updated {len(updated_rows)} rows ({updated_rows}) in '{path}'."
            
#         # Handle updating a single row
#         elif row is not None:
#             if not isinstance(row, int) or row < 0:
#                 return "Error: Row number must be a non-negative integer."
                
#             if row >= total_lines:
#                 return f"Error: Row {row} is out of range (file has {total_lines} lines)."
                
#             # If substring is provided, only replace that part
#             if substring is not None:
#                 # Only update if substring exists in the line
#                 if substring in lines[row]:
#                     original_line = lines[row]
#                     lines[row] = lines[row].replace(substring, content)
#                     # Ensure line ends with newline if original did
#                     if original_line.endswith('\n') and not lines[row].endswith('\n'):
#                         lines[row] += '\n'
#                 else:
#                     return f"Substring '{substring}' not found in row {row}."
#             else:
#                 # Otherwise, replace the entire line
#                 lines[row] = content_lines[0] if content_lines else "\n"
            
#             # Write back to the file
#             with open(path, 'w', encoding='utf-8') as file:
#                 file.writelines(lines)
                
#             if substring is not None:
#                 return f"Successfully updated substring in row {row} in '{path}'."
#             else:
#                 return f"Successfully updated row {row} in '{path}'."
        
#         # If neither row nor rows specified, update the entire file
#         else:
#             if substring is not None:
#                 # Replace substring throughout the file
#                 updated_count = 0
#                 for i in range(len(lines)):
#                     if substring in lines[i]:
#                         original_line = lines[i]
#                         lines[i] = lines[i].replace(substring, content)
#                         # Ensure line ends with newline if original did
#                         if original_line.endswith('\n') and not lines[i].endswith('\n'):
#                             lines[i] += '\n'
#                         updated_count += 1
                
#                 with open(path, 'w', encoding='utf-8') as file:
#                     file.writelines(lines)
                
#                 if updated_count == 0:
#                     return f"Substring '{substring}' not found in any line of '{path}'."
#                 return f"Successfully updated substring in {updated_count} lines in '{path}'."
#             else:
#                 # Replace entire file content
#                 with open(path, 'w', encoding='utf-8') as file:
#                     file.write(content)
#                 return f"Successfully updated all content in '{path}'."
            
#     except PermissionError:
#         return f"Error: No permission to modify file '{path}'."
#     except Exception as e:
#         return f"Error updating content: {str(e)}"


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