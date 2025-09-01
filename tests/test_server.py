import sys
import types
import time
import unittest


# Prepare dummy modules for dotenv and mcp.server.fastmcp before importing server
dotenv_mod = types.ModuleType('dotenv')
def _dotenv_values(path):
    return {}
dotenv_mod.dotenv_values = _dotenv_values
sys.modules['dotenv'] = dotenv_mod

fastmcp_mod = types.ModuleType('mcp.server.fastmcp')
class DummyFastMCP:
    def __init__(self, name: str):
        self.name = name
    def tool(self, description: str):
        def decorator(fn):
            return fn
        return decorator
    def run(self, transport: str = 'stdio'):
        return None
class DummyContext:
    pass
fastmcp_mod.FastMCP = DummyFastMCP
fastmcp_mod.Context = DummyContext
# Also register parent packages
mcp_pkg = types.ModuleType('mcp')
server_pkg = types.ModuleType('mcp.server')
sys.modules['mcp'] = mcp_pkg
sys.modules['mcp.server'] = server_pkg
sys.modules['mcp.server.fastmcp'] = fastmcp_mod

# Now import the server module under test
import server  # type: ignore


class FakeInterpreter:
    def __init__(self):
        self.container_name = 'fake-container'
        self.dirs = set()
        self.files = {}
        self.reset_called = 0
        self.exec_calls = []
        self.exec_file_calls = []
        self.cp_in_calls = []
        self.cp_out_calls = []

    def ensure_container(self):
        return None

    def make_dir(self, path: str):
        self.dirs.add(path)

    def remove_dir(self, path: str):
        # Remove dir and any nested file entries
        self.dirs.discard(path)
        for k in list(self.files.keys()):
            if k.startswith(path.rstrip('/') + '/'):
                self.files.pop(k, None)

    def write_file(self, path: str, content: str):
        # Create parent dir implicitly
        parent = '/'.join(path.strip('/').split('/')[:-1])
        if parent:
            self.dirs.add('/' + parent if not parent.startswith('/') else parent)
        self.files[path] = content
        return "Exit code: 0"

    def read_file(self, path: str):
        if path in self.files:
            return self.files[path], 0
        return "", 1

    def run_command(self, cmd, capture_output=False, check=True, input=None):
        # Simulate minimal commands used by server
        text = ""
        rc = 0
        if cmd[:3] == ['exec', self.container_name, 'sh'] and '-lc' in cmd:
            shell_cmd = cmd[-1]
            if shell_cmd.startswith('test -d '):
                target = shell_cmd[len('test -d '):].strip()
                rc = 0 if target in self.dirs else 1
            elif shell_cmd.startswith('rm -f '):
                # ignore
                rc = 0
            elif shell_cmd.startswith('stat -c %Y '):
                # no mtime info, return 0 meaning unknown
                text = '0'
                rc = 0
            else:
                rc = 0
        else:
            rc = 0
        class R:
            def __init__(self, stdout, returncode):
                self.stdout = stdout
                self.stderr = ''
                self.returncode = returncode
        return R(text, rc)

    def exec_code(self, code: str, workdir: str | None = None):
        self.exec_calls.append((code, workdir))
        return f"exec in {workdir}"

    def exec_container_file(self, container_path: str, workdir: str | None = None):
        self.exec_file_calls.append((container_path, workdir))
        return f"exec file {container_path} in {workdir}"

    def cp_in(self, src: str, dst: str):
        self.cp_in_calls.append((src, dst))
        return f"Copied host:{src} to container:{dst}"

    def cp_out(self, src: str, dst: str):
        self.cp_out_calls.append((src, dst))
        return f"Copied container:{src} to host:{dst}"

    def list_packages(self):
        return "pkgA\nExit code: 0"

    def reset(self):
        self.reset_called += 1
        self.dirs.clear()
        self.files.clear()
        return "reset"


class TestServerSessions(unittest.TestCase):
    def setUp(self):
        # Fresh fake interpreter per test
        self.fake = FakeInterpreter()
        server.interpreter = self.fake
        # Reset in-memory session state
        with server._lock:
            server._sessions.clear()
            server._current_session_id = None

    def test_init_creates_current_session_and_run_code_uses_it(self):
        sid = server.init(None)
        self.assertTrue(sid)
        current = server._get_current_session()
        self.assertEqual(current, sid)
        # Session directory should be created inside container
        self.assertIn(f"/workspace/sessions/{sid}", self.fake.dirs)
        out = server.run_code("print('x')")
        self.assertIn(f"/workspace/sessions/{sid}", out)

    def test_run_code_ephemeral_does_not_change_current(self):
        sid = server.init(None)
        before = server._get_current_session()
        out = server.run_code_ephemeral("print('x')")
        # Should mention a different session dir
        self.assertIn("/workspace/sessions/", out)
        self.assertNotIn(f"/workspace/sessions/{sid}", out)
        after = server._get_current_session()
        self.assertEqual(before, after)

    def test_edit_and_run_file(self):
        sid = server.init(None)
        res = server.edit_file("code/foo.py", "print('ok')\n")
        # File should be written under session dir path in fake store
        sess_dir = f"/workspace/sessions/{sid}"
        self.assertIn(f"{sess_dir}/code/foo.py", self.fake.files)
        run_res = server.run_file("code/foo.py")
        self.assertIn(f"{sess_dir}/code/foo.py", run_res)

    def test_cp_in_out_paths_are_relative_to_session(self):
        sid = server.init(None)
        msg_in = server.cp_in("host.txt", "cont.txt")
        self.assertIn(f"/workspace/sessions/{sid}/cont.txt", msg_in)
        msg_out = server.cp_out("cont.txt", "host_out.txt")
        self.assertIn("container:/workspace/sessions/" + sid + "/cont.txt", msg_out)
        self.assertIn("host:host_out.txt", msg_out)

    def test_close_current_session(self):
        sid = server.init(None)
        msg = server.close_current_session()
        self.assertEqual(msg, f"closed {sid}")
        self.assertIsNone(server._get_current_session())

    def test_reset_clears_sessions_and_calls_interpreter(self):
        server.init(None)
        res = server.reset(None)  # type: ignore
        self.assertEqual(res.splitlines()[-1], "reset")
        self.assertIsNone(server._get_current_session())
        self.assertEqual(len(server._sessions), 0)
        self.assertEqual(self.fake.reset_called, 1)


if __name__ == '__main__':
    unittest.main()
