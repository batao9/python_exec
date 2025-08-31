"""
MCP server exposing Docker-based Python code interpreter tools.

Now supports a per-connection "current session" so that callers do not
need to manually pass a session_id on each tool call. A session is
identified by a session_id issued by init(). Tools accept an optional
session_id. If omitted, the server will use the connection's current
session, creating one if necessary, and keep it for subsequent calls.
An explicit ephemeral one-shot mode is also provided via run_code_ephemeral.
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
# Current session per-connection. For stdio transport we assume one
# connection in-process, so a single global is sufficient.
_current_session_id: Optional[str] = None
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

def _get_current_session() -> Optional[str]:
    with _lock:
        return _current_session_id

def _set_current_session(session_id: Optional[str]) -> None:
    with _lock:
        global _current_session_id
        _current_session_id = session_id

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
    def __init__(self, session_id: Optional[str], *, use_current_if_missing: bool = True, ephemeral_if_missing: bool = False):
        self.user_session_id = session_id
        self.use_current_if_missing = use_current_if_missing
        self.ephemeral_if_missing = ephemeral_if_missing
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
            if self.ephemeral_if_missing:
                # create a one-shot session and remove it on exit
                self.session_id = _create_session()
                self.owns = True
            elif self.use_current_if_missing:
                # use current session if available; otherwise create and set current
                cur = _get_current_session()
                if cur and cur in _sessions:
                    self.session_id = cur
                else:
                    self.session_id = _create_session()
                    _set_current_session(self.session_id)
            else:
                raise ValueError("session_id is required")
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
    description='Start or ensure the Docker container, and create a new current session. '
                'Returns a session_id and sets it as the current session for this connection.'
)
def init(ctx: Context) -> str:
    """Start/ensure Docker container and create a new session. Returns session_id and sets it current."""
    interpreter.ensure_container()
    _ensure_base_dir()
    sid = _create_session()
    _set_current_session(sid)
    return sid

@mcp.tool(
    description='Run Python code inside the container. If session_id is omitted, uses the current session '
                '(creating one if needed).'
)
def run_code(code: str, session_id: str | None = None, ctx: Context | None = None) -> str:
    with _SessionContext(session_id, use_current_if_missing=True, ephemeral_if_missing=False) as sess:
        return interpreter.exec_code(code, workdir=sess.dir)

@mcp.tool(
    description='Run Python code in a one-shot ephemeral session and clean it up immediately.'
)
def run_code_ephemeral(code: str, ctx: Context | None = None) -> str:
    with _SessionContext(None, use_current_if_missing=False, ephemeral_if_missing=True) as sess:
        return interpreter.exec_code(code, workdir=sess.dir)

@mcp.tool(
    description='Run a Python script inside the container. Path must be relative to the session workspace. '
                'If session_id is omitted, uses the current session (creating one if needed).'
)
def run_file(path: str, session_id: str | None = None, ctx: Context | None = None) -> str:
    _ensure_relative_posix(path)
    with _SessionContext(session_id, use_current_if_missing=True, ephemeral_if_missing=False) as sess:
        effective = f"{sess.dir}/{path}"
        return interpreter.exec_container_file(effective, workdir=sess.dir)

def _ensure_relative_posix(path: str) -> None:
    from pathlib import PurePosixPath
    p = PurePosixPath(path)
    if p.is_absolute() or any(part == '..' for part in p.parts):
        raise ValueError('only relative paths without .. are allowed')

@mcp.tool(
    description='Upload a file from host UPLOAD_DIR into the container. container_path must be relative and '
                'is resolved under the session workspace. If session_id is omitted, uses the current session '
                '(creating one if needed).'
)
def cp_in(local_path: str, container_path: str | None, session_id: str | None = None, ctx: Context | None = None) -> str:
    with _SessionContext(session_id, use_current_if_missing=True, ephemeral_if_missing=False) as sess:
        if not container_path:
            base = os.path.basename(local_path)
            container_path = base
        _ensure_relative_posix(container_path)
        effective = f"{sess.dir}/{container_path}"
        return interpreter.cp_in(local_path, effective)

@mcp.tool(
    description='Download a file from the container to host DOWNLOAD_DIR. container_path must be relative to the '
                'session workspace. local_path defaults to basename. If session_id is omitted, uses the current '
                'session (creating one if needed).'
)
def cp_out(container_path: str, local_path: str | None, session_id: str | None = None, ctx: Context | None = None) -> str:
    with _SessionContext(session_id, use_current_if_missing=True, ephemeral_if_missing=False) as sess:
        _ensure_relative_posix(container_path)
        if not local_path:
            local_path = os.path.basename(container_path)
        effective_src = f"{sess.dir}/{container_path}"
        return interpreter.cp_out(effective_src, local_path)

@mcp.tool(
    description='Create or edit a file inside the container. container_path must be relative to the session '
                'workspace. If session_id is omitted, uses the current session (creating one if needed).'
)
def edit_file(container_path: str, content: str, session_id: str | None = None, ctx: Context | None = None) -> str:
    with _SessionContext(session_id, use_current_if_missing=True, ephemeral_if_missing=False) as sess:
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
    _set_current_session(None)
    return interpreter.reset()

@mcp.tool(
    description='Close a session immediately and remove its workspace.'
)
def close_session(session_id: str, ctx: Context | None = None) -> str:
    if not session_id:
        return "session_id is required"
    _remove_session(session_id)
    return f"closed {session_id}"

@mcp.tool(
    description='Get the current session_id for this connection (empty if none).'
)
def get_current_session(ctx: Context | None = None) -> str:
    return _get_current_session() or ""

@mcp.tool(
    description='Create a new session and set it as the current session for this connection.'
)
def new_current_session(ctx: Context | None = None) -> str:
    interpreter.ensure_container()
    _ensure_base_dir()
    sid = _create_session()
    _set_current_session(sid)
    return sid

@mcp.tool(
    description='Close the current session for this connection.'
)
def close_current_session(ctx: Context | None = None) -> str:
    sid = _get_current_session()
    if not sid:
        return "no current session"
    _remove_session(sid)
    _set_current_session(None)
    return f"closed {sid}"

if __name__ == "__main__":
    mcp.run(transport='stdio')
