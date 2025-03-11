# Import necessary Python standard libraries
import os          # For operating with file system, handling files and directory paths
import json        # For processing JSON format data
import subprocess  # For creating and managing subprocesses
import sys         # For accessing Python interpreter related variables and functions
import platform    # For getting current operating system information

def setup_venv():
    """
    Function to set up Python virtual environment
    
    Features:
    - Checks if Python version meets requirements (3.10+)
    - Creates Python virtual environment (if it doesn't exist)
    - Installs required dependencies in the newly created virtual environment
    
    No parameters required
    
    Returns: None
    """
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 10):
        print("Error: Python 3.10 or higher is required.")
        sys.exit(1)
    
    # Get absolute path of the directory containing the current script
    base_path = os.path.abspath(os.path.dirname(__file__))
    # Set virtual environment directory path, will create a directory named '.venv' under base_path
    venv_path = os.path.join(base_path, '.venv')
    # Flag whether a new virtual environment was created
    venv_created = False

    # Check if virtual environment already exists
    if not os.path.exists(venv_path):
        print("Creating virtual environment...")
        # Use Python's venv module to create virtual environment
        # sys.executable gets the path of the current Python interpreter
        subprocess.run([sys.executable, '-m', 'venv', venv_path], check=True)
        print("Virtual environment created successfully!")
        venv_created = True
    else:
        print("Virtual environment already exists.")
    
    # Determine pip and python executable paths based on operating system
    is_windows = platform.system() == "Windows"
    if is_windows:
        pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
        python_path = os.path.join(venv_path, 'Scripts', 'python.exe')
    else:
        pip_path = os.path.join(venv_path, 'bin', 'pip')
        python_path = os.path.join(venv_path, 'bin', 'python')
    
    # Install or update dependencies
    print("\nInstalling requirements...")
    # Install mcp package
    subprocess.run([pip_path, 'install', 'mcp'], check=True)
    
    # Also install dependencies from requirements.txt if it exists
    requirements_path = os.path.join(base_path, 'requirements.txt')
    if os.path.exists(requirements_path):
        subprocess.run([pip_path, 'install', '-r', requirements_path], check=True)
    
    print("Requirements installed successfully!")
    
    return python_path

def generate_mcp_config(python_path):
    """
    Function to generate MCP (Model Context Protocol) configuration file
    
    Features:
    - Creates configuration containing Python interpreter path and server script path
    - Saves configuration as JSON format file
    - Prints configuration information for different MCP clients
    
    Parameters:
    - python_path: Path to Python interpreter in the virtual environment
    
    Returns: None
    """
    # Get absolute path of the directory containing the current script
    base_path = os.path.abspath(os.path.dirname(__file__))
    
    # Path to Terminal Controller server script
    server_script_path = os.path.join(base_path, 'terminal_controller.py')
    
    # Create MCP configuration dictionary
    config = {
        "mcpServers": {
            "terminal-controller": {
                "command": python_path,
                "args": [server_script_path],
                "env": {
                    "PYTHONPATH": base_path
                }
            }
        }
    }
    
    # Save configuration to JSON file
    config_path = os.path.join(base_path, 'mcp-config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)  # indent=2 gives the JSON file good formatting

    # Print configuration information
    print(f"\nMCP configuration has been written to: {config_path}")    
    print(f"\nMCP configuration for Cursor:\n\n{python_path} {server_script_path}")
    print("\nMCP configuration for Windsurf/Claude Desktop:")
    print(json.dumps(config, indent=2))
    
    # Provide instructions for adding configuration to Claude Desktop configuration file
    if platform.system() == "Windows":
        claude_config_path = os.path.expandvars("%APPDATA%\\Claude\\claude_desktop_config.json")
    else:  # macOS
        claude_config_path = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
    
    print(f"\nTo use with Claude Desktop, merge this configuration into: {claude_config_path}")

# Code executed when the script is run directly (not imported)
if __name__ == '__main__':
    # Execute main functions in sequence:
    # 1. Set up virtual environment and install dependencies
    python_path = setup_venv()
    # 2. Generate MCP configuration file
    generate_mcp_config(python_path)
    
    print("\nSetup complete! You can now use the Terminal Controller MCP server with compatible clients.")
