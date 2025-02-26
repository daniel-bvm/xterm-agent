# 导入必要的Python标准库
import os          # 用于操作文件系统、处理文件和目录路径
import json        # 用于处理JSON格式的数据
import subprocess  # 用于创建和管理子进程
import sys         # 用于访问Python解释器相关的变量和函数
import platform    # 用于获取当前操作系统信息

def setup_venv():
    """
    设置Python虚拟环境的函数
    
    功能：
    - 检查Python版本是否满足要求（3.10+）
    - 创建Python虚拟环境（如果不存在）
    - 在新创建的虚拟环境中安装所需的依赖包
    
    不需要参数
    
    返回值：无
    """
    # 检查Python版本
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 10):
        print("Error: Python 3.10 or higher is required.")
        sys.exit(1)
    
    # 获取当前脚本文件所在目录的绝对路径
    base_path = os.path.abspath(os.path.dirname(__file__))
    # 设置虚拟环境目录路径，将在base_path下创建名为'.venv'的目录
    venv_path = os.path.join(base_path, '.venv')
    # 标记是否新创建了虚拟环境
    venv_created = False

    # 检查虚拟环境是否已存在
    if not os.path.exists(venv_path):
        print("Creating virtual environment...")
        # 使用Python的venv模块创建虚拟环境
        # sys.executable 获取当前Python解释器的路径
        subprocess.run([sys.executable, '-m', 'venv', venv_path], check=True)
        print("Virtual environment created successfully!")
        venv_created = True
    else:
        print("Virtual environment already exists.")
    
    # 根据操作系统确定pip和python可执行文件的路径
    is_windows = platform.system() == "Windows"
    if is_windows:
        pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
        python_path = os.path.join(venv_path, 'Scripts', 'python.exe')
    else:
        pip_path = os.path.join(venv_path, 'bin', 'pip')
        python_path = os.path.join(venv_path, 'bin', 'python')
    
    # 安装或更新依赖包
    print("\nInstalling requirements...")
    # 安装mcp包
    subprocess.run([pip_path, 'install', 'mcp'], check=True)
    
    # 如果有requirements.txt文件，也安装其中的依赖
    requirements_path = os.path.join(base_path, 'requirements.txt')
    if os.path.exists(requirements_path):
        subprocess.run([pip_path, 'install', '-r', requirements_path], check=True)
    
    print("Requirements installed successfully!")
    
    return python_path

def generate_mcp_config(python_path):
    """
    生成MCP（Model Context Protocol）配置文件的函数
    
    功能：
    - 创建包含Python解释器路径和服务器脚本路径的配置
    - 将配置保存为JSON格式文件
    - 打印配置信息供不同MCP客户端使用
    
    参数：
    - python_path：虚拟环境中Python解释器的路径
    
    返回值：无
    """
    # 获取当前脚本文件所在目录的绝对路径
    base_path = os.path.abspath(os.path.dirname(__file__))
    
    # Terminal Controller服务器脚本的路径
    server_script_path = os.path.join(base_path, 'terminal_controller.py')
    
    # 创建MCP配置字典
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
    
    # 将配置保存到JSON文件
    config_path = os.path.join(base_path, 'mcp-config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)  # indent=2 使JSON文件具有良好的格式

    # 打印配置信息
    print(f"\nMCP configuration has been written to: {config_path}")    
    print(f"\nMCP configuration for Cursor:\n\n{python_path} {server_script_path}")
    print("\nMCP configuration for Windsurf/Claude Desktop:")
    print(json.dumps(config, indent=2))
    
    # 提供将配置添加到Claude Desktop配置文件的说明
    if platform.system() == "Windows":
        claude_config_path = os.path.expandvars("%APPDATA%\\Claude\\claude_desktop_config.json")
    else:  # macOS
        claude_config_path = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
    
    print(f"\nTo use with Claude Desktop, merge this configuration into: {claude_config_path}")

# 当脚本直接运行（而不是被导入）时执行的代码
if __name__ == '__main__':
    # 按顺序执行主要功能：
    # 1. 设置虚拟环境并安装依赖
    python_path = setup_venv()
    # 2. 生成MCP配置文件
    generate_mcp_config(python_path)
    
    print("\nSetup complete! You can now use the Terminal Controller MCP server with compatible clients.")