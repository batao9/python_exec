"""
MCP server exposing Docker-based Python code interpreter tools.

Now supports ephemeral per-response sessions so that files from one
interaction do not leak into another. A session is identified by a
session_id issued by init(). Each tool accepts an optional session_id.
If omitted, a one-shot ephemeral session is created for that single
call and then cleaned up immediately.
"""
# Standard library imports
import sys
import os
import argparse
from pathlib import Path
import time
import threading
import secrets
from typing import Optional

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

# -----------------------------
# Session management (in-process)
# -----------------------------
SESSION_BASE_DIR = "/workspace/sessions"
SESSION_TTL_SECONDS = int(os.environ.get("PY_EXEC_SESSION_TTL", "600"))
SESSION_MAX = int(os.environ.get("PY_EXEC_SESSION_MAX", "32"))

_sessions: dict[str, tuple[float, float]] = {}
_lock = threading.Lock()
_janitor_started = False

def _ensure_base_dir():
    # interpreter.ensure_container() is called by the caller
    try:
        if hasattr(interpreter, 'make_dir'):
            interpreter.make_dir(SESSION_BASE_DIR)
    except Exception:
        pass

def _new_session_id() -> str:
    return secrets.token_hex(8)

def _session_path(session_id: str) -> str:
    return f"{SESSION_BASE_DIR}/{session_id}"

def _touch(session_id: str) -> None:
    now = time.time()
    with _lock:
        if session_id in _sessions:
            created = _sessions[session_id][1]
            _sessions[session_id] = (now, created)

def _create_session() -> str:
    session_id = _new_session_id()
    session_dir = _session_path(session_id)
    if hasattr(interpreter, 'make_dir'):
            interpreter.make_dir(session_dir)
    now = time.time()
    with _lock:
        _sessions[session_id] = (now, now)
        if len(_sessions) > SESSION_MAX:
            to_remove = sorted(_sessions.items(), key=lambda kv: kv[1][0])[: len(_sessions) - SESSION_MAX]
            for sid, _ in to_remove:
                try:
                    interpreter.remove_dir(_session_path(sid))
                finally:
                    _sessions.pop(sid, None)
    return session_id

def _remove_session(session_id: str) -> None:
    with _lock:
        _sessions.pop(session_id, None)
    try:
        if hasattr(interpreter, 'remove_dir'):
            interpreter.remove_dir(_session_path(session_id))
    except Exception:
        pass

def _cleanup_expired():
    now = time.time()
    expired: list[str] = []
    with _lock:
        for sid, (last_used, _created) in list(_sessions.items()):
            if now - last_used > SESSION_TTL_SECONDS:
                expired.append(sid)
    for sid in expired:
        _remove_session(sid)

def _start_janitor_once():
    global _janitor_started
    if _janitor_started:
        return
    _janitor_started = True

    def _loop():
        while True:
            try:
                _cleanup_expired()
            except Exception:
                pass
            time.sleep(60)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()

_start_janitor_once()

class _SessionContext:
    def __init__(self, session_id: Optional[str]):
        self.user_session_id = session_id
        self.owns = False
        self.session_id: Optional[str] = None

    def __enter__(self):
        interpreter.ensure_container()
        _ensure_base_dir()
        if self.user_session_id:
            # Only allow previously created session IDs; do not auto-create directories
            with _lock:
                if self.user_session_id not in _sessions:
                    raise ValueError("invalid session_id (use init() to create one)")
            self.session_id = self.user_session_id
        else:
            self.session_id = _create_session()
            self.owns = True
        _touch(self.session_id)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.owns and self.session_id:
            _remove_session(self.session_id)
        return False

    @property
    def dir(self) -> str:
        if not self.session_id:
            raise RuntimeError("Session not initialized")
        return _session_path(self.session_id)

def _map_container_path(path: str, session_dir: str) -> str:
    if path.startswith('/'):
        return path
    return f"{session_dir}/{path}"

@mcp.tool(
    description='Start or ensure the Docker container, and create a fresh ephemeral session. '
                'Returns a session_id which you should pass to other tools during this reply.'
)
def init(ctx: Context) -> str:
    """Start/ensure Docker container and create a new session. Returns session_id."""
    interpreter.ensure_container()
    _ensure_base_dir()
    return _create_session()

@mcp.tool(
    description='Run Python code inside the container. Optional session_id enables an ephemeral workspace. '
                'If session_id is omitted, a one-shot session is created and cleaned up automatically.'
)
def run_code(code: str, session_id: str | None = None, ctx: Context | None = None) -> str:
    with _SessionContext(session_id) as sess:
        return interpreter.exec_code(code, workdir=sess.dir)

@mcp.tool(
    description='Run a Python script inside the container (session_id is required). '
                'Path must be relative to the session workspace.'
)
def run_file(path: str, session_id: str, ctx: Context | None = None) -> str:
    _ensure_relative_posix(path)
    with _SessionContext(session_id) as sess:
        effective = f"{sess.dir}/{path}"
        return interpreter.exec_container_file(effective, workdir=sess.dir)

def _ensure_relative_posix(path: str) -> None:
    from pathlib import PurePosixPath
    p = PurePosixPath(path)
    if p.is_absolute() or any(part == '..' for part in p.parts):
        raise ValueError('only relative paths without .. are allowed')

@mcp.tool(
    description='Upload a file from host UPLOAD_DIR into the container (session_id is required). '
                'container_path must be relative and is resolved under the session workspace.'
)
def cp_in(local_path: str, container_path: str | None, session_id: str, ctx: Context | None = None) -> str:
    with _SessionContext(session_id) as sess:
        if not container_path:
            base = os.path.basename(local_path)
            container_path = base
        _ensure_relative_posix(container_path)
        effective = f"{sess.dir}/{container_path}"
        return interpreter.cp_in(local_path, effective)

@mcp.tool(
    description='Download a file from the container to host DOWNLOAD_DIR (session_id is required). '
                'container_path must be relative to the session workspace. local_path defaults to basename.'
)
def cp_out(container_path: str, local_path: str | None, session_id: str, ctx: Context | None = None) -> str:
    with _SessionContext(session_id) as sess:
        _ensure_relative_posix(container_path)
        if not local_path:
            local_path = os.path.basename(container_path)
        effective_src = f"{sess.dir}/{container_path}"
        return interpreter.cp_out(effective_src, local_path)

@mcp.tool(
    description='Create or edit a file inside the container (session_id is required). '
                'container_path must be relative to the session workspace.'
)
def edit_file(container_path: str, content: str, session_id: str, ctx: Context | None = None) -> str:
    with _SessionContext(session_id) as sess:
        _ensure_relative_posix(container_path)
        effective = f"{sess.dir}/{container_path}"
        return interpreter.write_file(effective, content)

@mcp.tool(
    description='List installed Python packages inside the container.'
)
def list_packages(session_id: str | None = None, ctx: Context | None = None) -> str:
    interpreter.ensure_container()
    return interpreter.list_packages()

@mcp.tool(
    description='Reset the Docker container to initial state. All sessions are cleared.'
)
def reset(ctx: Context) -> str:
    with _lock:
        sids = list(_sessions.keys())
    for sid in sids:
        _remove_session(sid)
    return interpreter.reset()

@mcp.tool(
    description='Close a session immediately and remove its workspace.'
)
def close_session(session_id: str, ctx: Context | None = None) -> str:
    if not session_id:
        return "session_id is required"
    _remove_session(session_id)
    return f"closed {session_id}"

if __name__ == "__main__":
    mcp.run(transport='stdio')
