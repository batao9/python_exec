import os
import importlib
import unittest
from pathlib import Path


class WorkdirsEnvTest(unittest.TestCase):
    def setUp(self):
        # Reload server module for clean state
        import server
        self.server_mod = importlib.reload(server)
        self.module_dir = Path(self.server_mod.__file__).parent
        self.env_path = self.module_dir / '.env'
        # Backup existing .env
        if self.env_path.exists():
            self.env_backup = self.env_path.read_text()
        else:
            self.env_backup = None
        # Clear env vars
        self.orig = {k: os.environ.pop(k, None) for k in ('WORKDIR', 'WORKDIR_IN', 'WORKDIR_OUT')}
        # Create test dirs
        self.test_in = str((self.module_dir / 'test_in').resolve())
        self.test_out = str((self.module_dir / 'test_out').resolve())
        Path(self.test_in).mkdir(exist_ok=True)
        Path(self.test_out).mkdir(exist_ok=True)
        # Write .env
        self.env_path.write_text(f'WORKDIR_IN={self.test_in}\nWORKDIR_OUT={self.test_out}\n')
        # Reload server
        self.server_mod = importlib.reload(self.server_mod)

    def tearDown(self):
        # Restore .env
        if self.env_backup is not None:
            self.env_path.write_text(self.env_backup)
        elif self.env_path.exists():
            self.env_path.unlink()
        # Restore env vars
        for k, v in self.orig.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)
        # Cleanup dirs
        try:
            Path(self.test_in).rmdir()
            Path(self.test_out).rmdir()
        except Exception:
            pass
        # Reload server
        importlib.reload(self.server_mod)

    def test_separate_workdirs(self):
        interp = self.server_mod.interpreter
        self.assertEqual(str(interp.host_workdir_in), self.test_in)
        self.assertEqual(str(interp.host_workdir_out), self.test_out)


if __name__ == '__main__':
    unittest.main()