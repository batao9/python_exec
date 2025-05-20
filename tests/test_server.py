import unittest
import server


class FakeInterpreter:
    def __init__(self):
        self.calls = []

    def init_container(self):
        self.calls.append(('init_container', (), {}))
        return 'init_result'

    def ensure_container(self):
        self.calls.append(('ensure_container', (), {}))

    def exec_code(self, code):
        self.calls.append(('exec_code', (code,), {}))
        return f'exec_code_output for {code}'

    def exec_file(self, path):
        self.calls.append(('exec_file', (path,), {}))
        return f'exec_file_output for {path}'

    def cp_in(self, src, dst):
        self.calls.append(('cp_in', (src, dst), {}))
        return f'cp_in_output for {src}->{dst}'

    def cp_out(self, src, dst):
        self.calls.append(('cp_out', (src, dst), {}))
        return f'cp_out_output for {src}->{dst}'

    def install(self, packages):
        self.calls.append(('install', (packages,), {}))
        return f'install_output for {packages}'

    def reset(self):
        self.calls.append(('reset', (), {}))
        return 'reset_output'


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.fake = FakeInterpreter()
        server.interpreter = self.fake

    def test_init(self):
        result = server.init(None)
        self.assertEqual(result, 'init_result')
        self.assertEqual(self.fake.calls, [('init_container', (), {})])

    def test_run_code(self):
        code = 'print("hello")'
        result = server.run_code(code, None)
        self.assertEqual(result, f'exec_code_output for {code}')
        self.assertEqual(self.fake.calls[0][0], 'ensure_container')
        self.assertEqual(self.fake.calls[1], ('exec_code', (code,), {}))

    def test_run_file(self):
        path = 'script.py'
        result = server.run_file(path, None)
        self.assertEqual(result, f'exec_file_output for {path}')
        self.assertEqual(self.fake.calls[0][0], 'ensure_container')
        self.assertEqual(self.fake.calls[1], ('exec_file', (path,), {}))

    def test_cp_in(self):
        src = 'local.txt'
        dst = '/container.txt'
        result = server.cp_in(src, dst, None)
        self.assertEqual(result, f'cp_in_output for {src}->{dst}')
        self.assertEqual(self.fake.calls[0][0], 'ensure_container')
        self.assertEqual(self.fake.calls[1], ('cp_in', (src, dst), {}))

    def test_cp_out(self):
        src = '/container.txt'
        dst = 'local.txt'
        result = server.cp_out(src, dst, None)
        self.assertEqual(result, f'cp_out_output for {src}->{dst}')
        self.assertEqual(self.fake.calls[0][0], 'ensure_container')
        self.assertEqual(self.fake.calls[1], ('cp_out', (src, dst), {}))

    def test_install(self):
        pkgs = ['requests', 'numpy']
        result = server.install(pkgs, None)
        self.assertEqual(result, f'install_output for {pkgs}')
        self.assertEqual(self.fake.calls[0][0], 'ensure_container')
        self.assertEqual(self.fake.calls[1], ('install', (pkgs,), {}))

    def test_reset(self):
        result = server.reset(None)
        self.assertEqual(result, 'reset_output')
        self.assertEqual(self.fake.calls, [('reset', (), {})])


if __name__ == '__main__':
    unittest.main()