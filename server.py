"""
MCP server exposing Docker-based Python code interpreter tools.

Provides tools to initialize and manage a Docker container,
execute Python code or scripts, transfer files, install packages,
and reset the container state.
"""
from mcp.server.fastmcp import FastMCP, Context

from docker_interpreter import DockerInterpreter

# Create the MCP server for the code interpreter
mcp = FastMCP("Docker Code Interpreter")

# Instantiate the interpreter with default container name and image
interpreter = DockerInterpreter()

@mcp.tool(description="Initialize or start the Docker container.")
def init(ctx: Context) -> str:
    """Initialize or start the Docker container and install MCP SDK."""
    return interpreter.init_container()

@mcp.tool(description="Execute Python code string inside the Docker container.")
def run_code(code: str, ctx: Context) -> str:
    """Execute Python code in the container."""
    interpreter.ensure_container()
    return interpreter.exec_code(code)

@mcp.tool(description="Execute a Python script file inside the Docker container by specifying its path within the container.")
def run_file(path: str, ctx: Context) -> str:
    """Execute a Python script file inside the container (container-internal path)."""
    interpreter.ensure_container()
    return interpreter.exec_container_file(path)

@mcp.tool(description="Upload a local file into the Docker container.")
def cp_in(local_path: str, container_path: str, ctx: Context) -> str:
    """Copy a file from host into the container."""
    interpreter.ensure_container()
    return interpreter.cp_in(local_path, container_path)

@mcp.tool(description="Download a file from the Docker container to the host.")
def cp_out(container_path: str, local_path: str, ctx: Context) -> str:
    """Copy a file from the container to the host."""
    interpreter.ensure_container()
    return interpreter.cp_out(container_path, local_path)

@mcp.tool(description="List installed Python packages inside the Docker container.")
def list_packages(ctx: Context) -> str:
    """List installed Python packages inside the container."""
    interpreter.ensure_container()
    return interpreter.list_packages()

@mcp.tool(description="Reset the Docker container to initial state.")
def reset(ctx: Context) -> str:
    """Reset the Docker container, removing and recreating it."""
    return interpreter.reset()

if __name__ == "__main__":
    mcp.run()