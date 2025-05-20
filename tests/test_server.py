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

    def exec_container_file(self, path):
        self.calls.append(('exec_container_file', (path,), {}))
        return f'exec_container_file_output for {path}'

    def exec_file(self, path):
        self.calls.append(('exec_file', (path,), {}))
        return f'exec_file_output for {path}'

    def cp_in(self, src, dst):
        self.calls.append(('cp_in', (src, dst), {}))
        return f'cp_in_output for {src}->{dst}'

    def cp_out(self, src, dst):
        self.calls.append(('cp_out', (src, dst), {}))
        return f'cp_out_output for {src}->{dst}'

    def list_packages(self):
        self.calls.append(('list_packages', (), {}))
        return 'list_packages_output'
    def write_file(self, container_path, content):
        self.calls.append(('write_file', (container_path, content), {}))
        return f'write_file_output for {container_path}'

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
        self.assertEqual(result, f'exec_container_file_output for {path}')
        self.assertEqual(self.fake.calls[0][0], 'ensure_container')
        self.assertEqual(self.fake.calls[1], ('exec_container_file', (path,), {}))

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

    def test_list_packages(self):
        result = server.list_packages(None)
        self.assertEqual(result, 'list_packages_output')
        self.assertEqual(self.fake.calls[0][0], 'ensure_container')
        self.assertEqual(self.fake.calls[1], ('list_packages', (), {}))

    def test_reset(self):
        result = server.reset(None)
        self.assertEqual(result, 'reset_output')
        self.assertEqual(self.fake.calls, [('reset', (), {})])
    
    def test_edit_file_fullpath(self):
        path = '/data/config.txt'
        content = 'hello world'
        result = server.edit_file(path, content, None)
        self.assertEqual(result, f'write_file_output for {path}')
        self.assertEqual(self.fake.calls[0][0], 'ensure_container')
        self.assertEqual(self.fake.calls[1], ('write_file', (path, content), {}))

    def test_edit_file_filename(self):
        filename = 'notes.md'
        content = 'markdown content'
        expected = '/workspace/notes.md'
        result = server.edit_file(filename, content, None)
        self.assertEqual(result, f'write_file_output for {expected}')
        self.assertEqual(self.fake.calls[0][0], 'ensure_container')
        self.assertEqual(self.fake.calls[1], ('write_file', (expected, content), {}))
    
    def test_cp_in_default(self):
        src = 'file.txt'
        expected = '/workspace/file.txt'
        result = server.cp_in(src, None, None)
        self.assertEqual(result, f'cp_in_output for {src}->{expected}')
        self.assertEqual(self.fake.calls[0][0], 'ensure_container')
        self.assertEqual(self.fake.calls[1], ('cp_in', (src, expected), {}))

    def test_cp_out_default(self):
        container_src = '/container/path/data.csv'
        expected = 'data.csv'
        result = server.cp_out(container_src, None, None)
        self.assertEqual(result, f'cp_out_output for {container_src}->{expected}')
        self.assertEqual(self.fake.calls[0][0], 'ensure_container')
        self.assertEqual(self.fake.calls[1], ('cp_out', (container_src, expected), {}))
    
    def test_cp_out_filename_only(self):
        # When only filename is given, src is treated as /workspace/<filename>
        filename = 'report.txt'
        expected_src = f'/workspace/{filename}'
        expected_dst = filename
        result = server.cp_out(filename, None, None)
        self.assertEqual(result, f'cp_out_output for {expected_src}->{expected_dst}')
        self.assertEqual(self.fake.calls[0][0], 'ensure_container')
        self.assertEqual(self.fake.calls[1], ('cp_out', (expected_src, expected_dst), {}))


if __name__ == '__main__':
    unittest.main()