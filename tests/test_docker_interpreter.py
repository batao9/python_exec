import unittest
import subprocess
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


if __name__ == "__main__":
    unittest.main()