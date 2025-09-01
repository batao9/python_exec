import os
import random
import string
import subprocess
from pathlib import Path

import pytest

from docker_interpreter import DockerInterpreter


def _docker_available() -> bool:
    try:
        subprocess.run(["docker", "ps"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _docker_available(), reason="Docker is not available in the test environment")


@pytest.fixture()
def tmp_in_out(tmp_path: Path):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()
    return in_dir, out_dir


@pytest.fixture()
def container_name():
    # Create a random container name to avoid collisions
    rand = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    name = f"mcp-ci-{rand}"
    try:
        # Ensure a Python container is running and idle
        subprocess.run(
            [
                "docker", "run", "-d",
                "--name", name,
                "-w", "/workspace",
                "python:3.11-slim",
                "tail", "-f", "/dev/null",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        pytest.skip(f"Failed to start docker container: {e}")
    try:
        yield name
    finally:
        subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


@pytest.fixture()
def interp(container_name: str, tmp_in_out):
    in_dir, out_dir = tmp_in_out
    return DockerInterpreter(
        container_name=container_name,
        image="python:3.11-slim",
        host_workdir_in=str(in_dir),
        host_workdir_out=str(out_dir),
    )


def test_container_running(interp: DockerInterpreter):
    assert interp.container_exists() is True
    assert interp.container_running() is True


def test_exec_code_prints_and_exit_code(interp: DockerInterpreter):
    out = interp.exec_code("print('hello-docker')")
    assert "hello-docker" in out
    assert "Exit code: 0" in out


def test_write_and_run_file(interp: DockerInterpreter):
    # Write a python file inside the container and execute it
    path = "/workspace/test_script.py"
    content = "print('from-file')\n"
    res = interp.write_file(path, content)
    assert "Exit code: 0" in res
    run_res = interp.exec_container_file(path)
    assert "from-file" in run_res
    assert "Exit code: 0" in run_res


def test_make_and_remove_dir(interp: DockerInterpreter):
    d = "/workspace/adir"
    interp.make_dir(d)
    # verify exists
    chk = subprocess.run(["docker", "exec", interp.container_name, "test", "-d", d])
    assert chk.returncode == 0
    interp.remove_dir(d)
    chk2 = subprocess.run(["docker", "exec", interp.container_name, "test", "-d", d])
    assert chk2.returncode != 0


def test_cp_in_and_cp_out(interp: DockerInterpreter, tmp_in_out):
    in_dir, out_dir = tmp_in_out
    # Create a host file under input dir
    src = in_dir / "hello.txt"
    data = "hello via docker\n"
    src.write_text(data)
    msg_in = interp.cp_in("hello.txt", "/workspace/hello.txt")
    assert "Copied host:hello.txt to container:/workspace/hello.txt" in msg_in
    # Verify content inside container
    cat = subprocess.run(
        ["docker", "exec", interp.container_name, "sh", "-lc", "cat /workspace/hello.txt"],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert cat.stdout == data

    # Prepare a file inside container for cp_out
    subprocess.run(
        ["docker", "exec", interp.container_name, "sh", "-lc", "printf '%s' 'world-out' > /workspace/out.txt"],
        check=True,
    )
    msg_out = interp.cp_out("/workspace/out.txt", "result.txt")
    assert "Copied container:/workspace/out.txt to host:result.txt" in msg_out
    # Verify written to host output dir
    dest = out_dir / "result.txt"
    assert dest.exists()
    assert dest.read_text() == "world-out"


def test_exec_code_with_workdir(interp: DockerInterpreter):
    # Create subdir and write relative file via workdir
    sub = "/workspace/subdir"
    interp.make_dir(sub)
    code = "open('rel.txt','w').write('ok')\n"
    out = interp.exec_code(code, workdir=sub)
    assert "Exit code: 0" in out
    chk = subprocess.run(["docker", "exec", interp.container_name, "sh", "-lc", "cat /workspace/subdir/rel.txt"], stdout=subprocess.PIPE, text=True)
    assert chk.stdout == "ok"
