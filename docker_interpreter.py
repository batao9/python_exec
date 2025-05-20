import subprocess


from pathlib import Path

class DockerInterpreter:
    def __init__(self, container_name='mcp-code-interpreter', image='python:3.10-slim', host_workdir: str = None):
        """Initialize interpreter with container settings and host working directory."""
        self.container_name = container_name
        self.image = image
        if host_workdir:
            self.host_workdir = Path(host_workdir).resolve()
        else:
            self.host_workdir = Path.cwd().resolve()
        if not self.host_workdir.is_dir():
            raise ValueError(f"Host working directory does not exist: {self.host_workdir}")

    def run_command(self, cmd, capture_output=False, check=True, input=None):
        full_cmd = ['docker'] + cmd
        return subprocess.run(
            full_cmd,
            capture_output=capture_output,
            text=True,
            check=check,
            input=input,
        )

    def container_exists(self):
        result = self.run_command(
            ['ps', '-a', '--filter', f'name={self.container_name}', '--format', '{{.Names}}'],
            capture_output=True,
        )
        return self.container_name in result.stdout.splitlines()

    def container_running(self):
        result = self.run_command(
            ['ps', '--filter', f'name={self.container_name}', '--format', '{{.Names}}'],
            capture_output=True,
        )
        return self.container_name in result.stdout.splitlines()

    def init_container(self) -> str:
        """Create or start the Docker container, and install MCP SDK."""
        messages: list[str] = []
        if self.container_exists():
            if self.container_running():
                messages.append(f"Container '{self.container_name}' is already running.")
                return "\n".join(messages)
            messages.append(f"Starting existing container '{self.container_name}'.")
            self.run_command(['start', self.container_name])
        else:
            messages.append(f"Creating and starting container '{self.container_name}'.")
            self.run_command([
                'run', '-d',
                '--name', self.container_name,
                '-w', '/workspace',
                self.image,
                'tail', '-f', '/dev/null',
            ])

        messages.append("Installing/upgrading pip and Model Context Protocol SDK inside container...")
        self.run_command(['exec', self.container_name, 'pip', 'install', '--upgrade', 'pip'])
        self.run_command(['exec', self.container_name, 'pip', 'install', 'mcp[cli]'])
        return "\n".join(messages)

    def ensure_container(self) -> None:
        if not self.container_running():
            self.init_container()

    def exec_code(self, code: str) -> str:
        """Execute given Python code string inside the container."""
        result = self.run_command(
            ['exec', '-i', self.container_name, 'python'],
            capture_output=True,
            check=False,
            input=code,
        )
        output = result.stdout or ""
        if result.stderr:
            output += f"\nstderr:\n{result.stderr}"
        output += f"\nExit code: {result.returncode}"
        return output

    def exec_file(self, local_path: str) -> str:
        """Copy local file into container workspace and execute it."""
        import os

        basename = os.path.basename(local_path)
        dest = f'/workspace/{basename}'
        self.cp_in(local_path, dest)
        result = self.run_command(
            ['exec', self.container_name, 'python', dest],
            capture_output=True,
            check=False,
        )
        output = result.stdout or ""
        if result.stderr:
            output += f"\nstderr:\n{result.stderr}"
        output += f"\nExit code: {result.returncode}"
        return output
    
    def exec_container_file(self, container_path: str) -> str:
        """Execute a Python script file at the given path inside the container."""
        result = self.run_command(
            ['exec', self.container_name, 'python', container_path],
            capture_output=True,
            check=False,
        )
        output = result.stdout or ""
        if result.stderr:
            output += f"\nstderr:\n{result.stderr}"
        output += f"\nExit code: {result.returncode}"
        return output
    
    def write_file(self, container_path: str, content: str) -> str:
        """Create or overwrite a file inside the container with the given content."""
        # Use shell redirection to write content into the container file
        cmd = ['exec', '-i', self.container_name, 'sh', '-c', f'cat > {container_path}']
        result = self.run_command(
            cmd,
            capture_output=True,
            check=False,
            input=content,
        )
        output = result.stdout or ""
        if result.stderr:
            output += f"\nstderr:\n{result.stderr}"
        output += f"\nExit code: {result.returncode}"
        return output

    def cp_in(self, src: str, dst: str) -> str:
        """Copy a file from host working directory into container at dst."""
        # Resolve and validate source path under host_workdir
        src_path = (self.host_workdir / src).resolve()
        if self.host_workdir not in src_path.parents and src_path != self.host_workdir:
            raise ValueError(f"Invalid source path: {src}")
        self.run_command(['cp', str(src_path), f'{self.container_name}:{dst}'])
        rel_src = src_path.relative_to(self.host_workdir).as_posix()
        return f"Copied host:{rel_src} to container:{dst}"

    def cp_out(self, src: str, dst: str) -> str:
        """Copy a file from container at src to host working directory at dst."""
        # Resolve and validate destination path under host_workdir
        dst_path = (self.host_workdir / dst).resolve()
        if self.host_workdir not in dst_path.parents and dst_path != self.host_workdir:
            raise ValueError(f"Invalid destination path: {dst}")
        self.run_command(['cp', f'{self.container_name}:{src}', str(dst_path)])
        rel_dst = dst_path.relative_to(self.host_workdir).as_posix()
        return f"Copied container:{src} to host:{rel_dst}"

    def list_packages(self) -> str:
        """List installed Python packages inside the container."""
        result = self.run_command(
            ['exec', self.container_name, 'pip', 'list'],
            capture_output=True,
            check=False,
        )
        output = result.stdout or ""
        if result.stderr:
            output += f"\nstderr:\n{result.stderr}"
        output += f"\nExit code: {result.returncode}"
        return output

    def reset(self) -> str:
        """Remove and recreate the container, resetting its state."""
        messages: list[str] = []
        if self.container_exists():
            messages.append(f"Removing container '{self.container_name}'...")
            self.run_command(['rm', '-f', self.container_name])
        init_msg = self.init_container()
        messages.append(init_msg)
        return "\n".join(messages)