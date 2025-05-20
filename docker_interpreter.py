import subprocess


class DockerInterpreter:
    def __init__(self, container_name='mcp-code-interpreter', image='python:3.10-slim'):
        self.container_name = container_name
        self.image = image

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

    def cp_in(self, src: str, dst: str) -> str:
        """Copy file from host (src) into container at dst."""
        self.run_command(['cp', src, f'{self.container_name}:{dst}'])
        return f"Copied host:{src} to container:{dst}"

    def cp_out(self, src: str, dst: str) -> str:
        """Copy file from container (src) to host at dst."""
        self.run_command(['cp', f'{self.container_name}:{src}', dst])
        return f"Copied container:{src} to host:{dst}"

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