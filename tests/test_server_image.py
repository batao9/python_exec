import os
import importlib
import unittest
from pathlib import Path


class DockerImageEnvTest(unittest.TestCase):
    def setUp(self):
        # Backup existing .env
        import server
        self.server_mod = server
        self.module_dir = Path(self.server_mod.__file__).parent
        self.env_path = self.module_dir / '.env'
        if self.env_path.exists():
            self.env_backup = self.env_path.read_text()
        else:
            self.env_backup = None
        # Clear DOCKER_IMAGE env var
        self.orig_image_env = os.environ.pop('DOCKER_IMAGE', None)
        # Write .env with DOCKER_IMAGE
        self.test_image = 'python:3.9-slim'
        self.env_path.write_text(f'DOCKER_IMAGE={self.test_image}\n')
        # Reload server module to pick up new .env
        importlib.reload(self.server_mod)

    def tearDown(self):
        # Restore .env
        if self.env_backup is not None:
            self.env_path.write_text(self.env_backup)
        elif self.env_path.exists():
            self.env_path.unlink()
        # Restore DOCKER_IMAGE env var
        if self.orig_image_env is not None:
            os.environ['DOCKER_IMAGE'] = self.orig_image_env
        else:
            os.environ.pop('DOCKER_IMAGE', None)
        # Reload server module to reset state
        importlib.reload(self.server_mod)

    def test_docker_image_from_env(self):
        # The interpreter.image should reflect DOCKER_IMAGE
        from server import interpreter
        self.assertEqual(interpreter.image, self.test_image)


if __name__ == '__main__':
    unittest.main()