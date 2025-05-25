"""
MCP server exposing Docker-based Python code interpreter tools.

Provides tools to initialize and manage a Docker container,
execute Python code or scripts, transfer files, install packages,
and reset the container state.
"""
# Standard library imports
import sys
import os
import argparse
from pathlib import Path

# Third-party imports
from dotenv import dotenv_values
from mcp.server.fastmcp import FastMCP, Context

# Local imports
from docker_interpreter import DockerInterpreter

# Load .env variables (does not override existing environment vars)
dotenv_path = Path(__file__).parent / '.env'
env_config = dotenv_values(dotenv_path)

# Parse command-line overrides for input/output directories
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--WORKDIR_IN')
parser.add_argument('--WORKDIR_OUT')
args, remaining_args = parser.parse_known_args()
workdir_in_cli = args.WORKDIR_IN
workdir_out_cli = args.WORKDIR_OUT
# Ensure FastMCP sees only its own args
sys.argv = [sys.argv[0]] + remaining_args

# Determine Docker image
docker_image = env_config.get('DOCKER_IMAGE') or os.environ.get('DOCKER_IMAGE', 'python:3.10-slim')
# Determine base workdir (legacy WORKDIR)
base_workdir = env_config.get('WORKDIR') or os.environ.get('WORKDIR') or os.getcwd()
# Determine separate workdirs for input/output (CLI > .env > env var > base)
host_workdir_in = workdir_in_cli or env_config.get('WORKDIR_IN') or os.environ.get('WORKDIR_IN') or base_workdir
host_workdir_out = workdir_out_cli or env_config.get('WORKDIR_OUT') or os.environ.get('WORKDIR_OUT') or base_workdir

# Instantiate MCP server and Docker interpreter
mcp = FastMCP("Docker Code Interpreter")
interpreter = DockerInterpreter(
    image=docker_image,
    host_workdir_in=host_workdir_in,
    host_workdir_out=host_workdir_out,
)
# Legacy alias: host_workdir remains base_workdir
interpreter.host_workdir = Path(base_workdir).resolve()

@mcp.tool(
    description='Initialize or start the Docker container. \n'+
                'Use this tool if you need to initialize `/workspace` directory or start a Docker container .'
    )
def init(ctx: Context) -> str:
    """Initialize or start the Docker container and install MCP SDK."""
    return interpreter.init_container()

@mcp.tool(
    description='Docker Code Interpreter: Run Python Code: \n'+
                'code: Python code to execute. \n'+
                'Use this tool when you need to run Python code to get an answer. \n'+
                'Input must be a valid Python expression or statement. \n'+
                'Results are displayed in the console, so use functions like print() to print the results. \n'+
                'If you need to pass an output graph or file to the user, also use the cp_out tool. '
    )
def run_code(code: str, ctx: Context) -> str:
    """Execute Python code in the container."""
    interpreter.ensure_container()
    return interpreter.exec_code(code)

@mcp.tool(
    description='Docker Code Interpreter: Run Python Script: \n'+
                'path: filename (treated as /workspace/<filename>) or full container path. \n'+ 
                'Use this tool when you need to run a Python script to get an answer. \n'+
                'Input can be a relative path from the working directory or an absolute path. \n'+
                'The script will be executed in the container, and the output will be displayed in the console. \n'+
                'If you need to pass an output graph or file to the user, also use the cp_out tool. '
    )
def run_file(path: str, ctx: Context) -> str:
    """Execute a Python script file inside the container (container-internal path)."""
    interpreter.ensure_container()
    return interpreter.exec_container_file(path)

@mcp.tool(
    description='Docker Code Interpreter: Upload a file from host UPLOAD_DIR into the Docker container. \n'+
                'local_path: filename (treated as UPLOAD_DIR/<filename>)\n'+
                'container_path (optional): target path inside container, defaults to /workspace/<basename>.'+
                'Usually does not need to be specified.'
    )
def cp_in(local_path: str, container_path: str | None = None, ctx: Context = None) -> str:
    """Copy a file from host UPLOAD_DIR into the container.
    local_path: path relative to UPLOAD_DIR.
    container_path: optional path inside container (defaults to /workspace/<basename of local_path>)."""
    interpreter.ensure_container()
    # Determine default container path if not specified
    if not container_path:
        base = os.path.basename(local_path)
        container_path = f"/workspace/{base}"
    return interpreter.cp_in(local_path, container_path)

@mcp.tool(
    description='Docker Code Interpreter: Download a file from the Docker container into host DOWNLOAD_DIR. \n'+
                'container_path: filename (treated as /workspace/<filename>) or full container path. \n'+
                'local_path (optional): relative path under DOWNLOAD_DIR, defaults to basename of container_path.'+
                'Usually does not need to be specified.'
    )
def cp_out(container_path: str, local_path: str | None = None, ctx: Context = None) -> str:
    """Copy a file from the container to host DOWNLOAD_DIR.
    container_path: path inside container.
    local_path: optional relative path under DOWNLOAD_DIR (defaults to basename of container_path)."""
    interpreter.ensure_container()
    # Determine default local path if not specified
    if not local_path:
        local_path = os.path.basename(container_path)
    # If a bare filename is given, treat it as /workspace/<filename> inside container
    if not container_path.startswith('/') and '/' not in container_path:
        effective_src = f"/workspace/{container_path}"
    else:
        effective_src = container_path
    return interpreter.cp_out(effective_src, local_path)

@mcp.tool(
    description='Docker Code Interpreter: Edit or create a file inside the Docker container. \n'+
                'container_path: filename (treated as /workspace/<filename>) or full container path. \n'+
                'content: text to write into the file. \n'+
                'If you want to provide a file to a user, also use the cp_out tool.'
                
    )
def edit_file(container_path: str, content: str, ctx: Context) -> str:
    """Edit or create a file inside the container, writing the provided content.
    container_path: filename or full container path.
    content: file content to write."""
    interpreter.ensure_container()
    # Map bare filenames into /workspace
    if not container_path.startswith('/') and '/' not in container_path:
        effective_path = f"/workspace/{container_path}"
    else:
        effective_path = container_path
    return interpreter.write_file(effective_path, content)

@mcp.tool(
    description='Docker Code Interpreter: List installed Python packages inside the Docker container. \n'+
                'Use this tool when you need to list the installed packages in the container.'
    )
def list_packages(ctx: Context) -> str:
    """List installed Python packages inside the container."""
    interpreter.ensure_container()
    return interpreter.list_packages()

@mcp.tool(
    description='Docker Code Interpreter: Reset the Docker container to initial state. \n'+
                'Use this tool when you need to reset the container to its initial state.'
    )
def reset(ctx: Context) -> str:
    """Reset the Docker container, removing and recreating it."""
    return interpreter.reset()

if __name__ == "__main__":
    mcp.run(transport='stdio')