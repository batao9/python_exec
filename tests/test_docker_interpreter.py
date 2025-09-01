import os
import unittest
from pathlib import Path

from docker_interpreter import DockerInterpreter


class DummyResult:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class TestDockerInterpreter(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(self._get_tmpdir())
        self.indir = self.tmpdir / "in"
        self.outdir = self.tmpdir / "out"
        self.indir.mkdir(parents=True, exist_ok=True)
        self.outdir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        try:
            for p in sorted(self.tmpdir.rglob("*"), reverse=True):
                if p.is_file() or p.is_symlink():
                    p.unlink(missing_ok=True)
                else:
                    p.rmdir()
            self.tmpdir.rmdir()
        except Exception:
            pass

    def _get_tmpdir(self) -> str:
        base = Path.cwd() / ".tmp_test_dirs"
        base.mkdir(exist_ok=True)
        pid = os.getpid()
        for i in range(1000):
            d = base / f"t{pid}_{i}"
            if not d.exists():
                return str(d)
        raise RuntimeError("Unable to allocate temp directory")

    def _make_interpreter(self):
        calls = []
        interp = DockerInterpreter(
            image="test-image",
            host_workdir_in=str(self.indir),
            host_workdir_out=str(self.outdir),
        )

        def fake_run(cmd, capture_output=False, check=True, input=None):
            calls.append({
                "cmd": cmd,
                "capture_output": capture_output,
                "check": check,
                "input": input,
            })
            return DummyResult("", "", 0)

        interp.run_command = fake_run  # type: ignore
        return interp, calls

    def test_cp_in_valid(self):
        interp, calls = self._make_interpreter()
        src = self.indir / "hello.txt"
        src.write_text("hello")
        msg = interp.cp_in("hello.txt", "/workspace/hello.txt")
        self.assertTrue(calls)
        self.assertEqual(calls[-1]["cmd"][0], "cp")
        self.assertIn(str(src.resolve()), calls[-1]["cmd"])  # source path
        self.assertIn(f"{interp.container_name}:/workspace/hello.txt", calls[-1]["cmd"])  # dest
        self.assertEqual(msg, "Copied host:hello.txt to container:/workspace/hello.txt")

    def test_cp_in_invalid_escape(self):
        interp, _ = self._make_interpreter()
        with self.assertRaises(ValueError):
            interp.cp_in("../outside.txt", "/workspace/x.txt")

    def test_cp_out_valid(self):
        interp, calls = self._make_interpreter()
        msg = interp.cp_out("/workspace/out.bin", "result.bin")
        self.assertTrue(calls)
        self.assertEqual(calls[-1]["cmd"][0], "cp")
        self.assertTrue(str(self.outdir.resolve()) in calls[-1]["cmd"][2])
        self.assertIn(f"{interp.container_name}:/workspace/out.bin", calls[-1]["cmd"][1])
        self.assertEqual(msg, "Copied container:/workspace/out.bin to host:result.bin")

    def test_exec_code_builds_command_and_formats_output(self):
        interp, calls = self._make_interpreter()

        def fake_run(cmd, capture_output=False, check=True, input=None):
            return DummyResult(stdout="out", stderr="err", returncode=3)

        interp.run_command = fake_run  # type: ignore
        output = interp.exec_code("print('x')", workdir="/workspace/sess/abc")
        self.assertIn("out", output)
        self.assertIn("stderr:\nerr", output)
        self.assertIn("Exit code: 3", output)

    def test_write_file_uses_shell_redirection(self):
        interp, calls = self._make_interpreter()

        def fake_run(cmd, capture_output=False, check=True, input=None):
            self.assertEqual(cmd[:3], ['exec', '-i', interp.container_name])
            return DummyResult(stdout="", stderr="", returncode=0)

        interp.run_command = fake_run  # type: ignore
        out = interp.write_file("/workspace/file.txt", "content")
        self.assertIn("Exit code: 0", out)


if __name__ == "__main__":
    unittest.main()
