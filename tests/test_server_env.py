import os
import importlib
import unittest
from pathlib import Path


class EnvFileWorkdirTest(unittest.TestCase):
    def setUp(self):
        # Determine server module and its directory
        import server
        self.server_mod = importlib.reload(server)
        self.module_dir = Path(self.server_mod.__file__).parent
        self.env_path = self.module_dir / '.env'
        # Backup existing .env
        if self.env_path.exists():
            self.env_backup = self.env_path.read_text()
        else:
            self.env_backup = None
        # Clear WORKDIR env var
        self.orig_workdir_env = os.environ.pop('WORKDIR', None)
        # Create a test workdir and write .env
        self.test_workdir = str((self.module_dir / 'test_workdir').resolve())
        Path(self.test_workdir).mkdir(exist_ok=True)
        self.env_path.write_text(f'WORKDIR={self.test_workdir}\n')
        # Reload server to pick up .env
        self.server_mod = importlib.reload(self.server_mod)

    def tearDown(self):
        # Restore .env
        if self.env_backup is not None:
            self.env_path.write_text(self.env_backup)
        elif self.env_path.exists():
            self.env_path.unlink()
        # Restore WORKDIR env var
        if self.orig_workdir_env is not None:
            os.environ['WORKDIR'] = self.orig_workdir_env
        else:
            os.environ.pop('WORKDIR', None)
        # Reload server to clear env effects
        importlib.reload(self.server_mod)
        # Cleanup test workdir
        try:
            Path(self.test_workdir).rmdir()
        except Exception:
            pass

    def test_workdir_from_envfile(self):
        # The interpreter should have host_workdir set from .env
        wd = self.server_mod.interpreter.host_workdir
        self.assertEqual(str(wd), self.test_workdir)


if __name__ == '__main__':
    unittest.main()