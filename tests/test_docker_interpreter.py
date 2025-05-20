import unittest
import subprocess
import tempfile
from pathlib import Path
from docker_interpreter import DockerInterpreter


class DockerInterpreterListTest(unittest.TestCase):
    def test_list_packages_success(self):
        di = DockerInterpreter(container_name="test", image="python:3.10-slim")
        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="pkg1 1.0\npkg2 2.0\n", stderr="")
        di.run_command = fake_run
        result = di.list_packages()
        self.assertIn("pkg1 1.0", result)
        self.assertIn("pkg2 2.0", result)
        self.assertTrue(result.strip().endswith("Exit code: 0"))

    def test_list_packages_error(self):
        di = DockerInterpreter(container_name="test", image="python:3.10-slim")
        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error occurred")
        di.run_command = fake_run
        result = di.list_packages()
        self.assertIn("stderr:\nerror occurred", result)
        self.assertTrue(result.strip().endswith("Exit code: 1"))


class DockerInterpreterPathTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmpdir.name).resolve()
        self.di = DockerInterpreter(container_name="test", image="python:3.10-slim", host_workdir=str(self.workdir))
        self.last_cmd = None
        def fake_run(cmd, *args, **kwargs):
            self.last_cmd = cmd
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        self.di.run_command = fake_run

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_cp_in_allowed(self):
        result = self.di.cp_in("file.txt", "/container/path")
        expected = ['cp', str(self.workdir / "file.txt"), 'test:/container/path']
        self.assertEqual(self.last_cmd, expected)
        self.assertEqual(result, "Copied host:file.txt to container:/container/path")

    def test_cp_in_disallowed(self):
        with self.assertRaises(ValueError):
            self.di.cp_in("../outside.txt", "/container/path")

    def test_cp_out_allowed(self):
        result = self.di.cp_out("/container/src.py", "out.txt")
        expected = ['cp', 'test:/container/src.py', str(self.workdir / "out.txt")]
        self.assertEqual(self.last_cmd, expected)
        self.assertEqual(result, "Copied container:/container/src.py to host:out.txt")

    def test_cp_out_disallowed(self):
        with self.assertRaises(ValueError):
            self.di.cp_out("/container/src.py", "../outside.txt")
   
class DockerInterpreterWriteTest(unittest.TestCase):
    def setUp(self):
        self.di = DockerInterpreter(container_name="test", image="python:3.10-slim")
        self.last_cmd = None
        self.last_input = None
        def fake_run(cmd, capture_output=False, check=True, input=None):
            self.last_cmd = cmd
            self.last_input = input
            # Simulate writing OK
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="OK\n", stderr="")
        self.di.run_command = fake_run

    def test_write_file_success(self):
        path = '/workspace/file.txt'
        content = 'data'
        result = self.di.write_file(path, content)
        expected_cmd = ['exec', '-i', 'test', 'sh', '-c', f'cat > {path}']
        self.assertEqual(self.last_cmd, expected_cmd)
        self.assertEqual(self.last_input, content)
        self.assertIn("OK", result)
        self.assertTrue(result.strip().endswith("Exit code: 0"))

    def test_write_file_error(self):
        def fake_run_err(cmd, capture_output=False, check=True, input=None):
            self.last_cmd = cmd
            self.last_input = input
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="err")
        self.di.run_command = fake_run_err
        path = '/workspace/file2.txt'
        content = 'fail'
        result = self.di.write_file(path, content)
        self.assertIn("stderr:\nerr", result)
        self.assertTrue(result.strip().endswith("Exit code: 1"))

if __name__ == "__main__":
    unittest.main()