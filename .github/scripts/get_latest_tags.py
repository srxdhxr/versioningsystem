import json
import subprocess
import sys
from typing import List, Tuple
import semver
import os

def run_command(command: List[str]) -> Tuple[str, str, int]:
    """
    Run a shell command and return stdout, stderr, and return code
    """
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate()
    return stdout.strip(), stderr.strip(), process.returncode


def get_current_version(step: str) -> str:
    """
    Get the current version for a step from git tags.
    Returns '1.0.0' if no tags exist.
    """
    stdout, _, _ = run_command(['git', 'tag', '-l', f'{step}-v*'])
    if not stdout:
        return '1.0.0'
    
    versions = []
    for tag in stdout.split('\n'):
        try:
            version = tag.replace(f'{step}-v', '')
            print(f"version for {tag} : {version}")
            semver.VersionInfo.parse(version)
            versions.append(version)
        except ValueError:
            continue
    
    if not versions:
        return '1.0.0'
    
    return str(max(versions, key=semver.VersionInfo.parse))


def configure_git():
    """
    Configure git with GitHub Actions bot credentials
    """
    commands = [
        ['git', 'config', '--local', 'user.email', 'github-actions[bot]@users.noreply.github.com'],
        ['git', 'config', '--local', 'user.name', 'github-actions[bot]']
    ]
    
    for cmd in commands:
        _, stderr, code = run_command(cmd)
        if code != 0:
            raise RuntimeError(f"Failed to configure git: {stderr}")



def main():
    # Get environment variables
    github_token = os.environ.get('GITHUB_TOKEN')
    repository = os.environ.get('GITHUB_REPOSITORY')
    modified_folders = os.environ.get('MODIFIED_FOLDERS')
    
    if not all([github_token, repository, modified_folders]):
        print("Missing required environment variables")
        sys.exit(1)
    
    # Configure git
    configure_git()

    try:
        folders = json.loads(modified_folders)
    except json.JSONDecodeError as e:
        print(f"Failed to parse STEPS_VERSIONS JSON: {e}")
        print(f"Received content: {steps_versions}")
        sys.exit(1)
    
    for folder in folders:
        print(f"Getting latest git tag for the folder: {folder}\n")
        latest_tag = get_current_version(folder)
        print(f"The latest tag is {latest_tag} for {folder}\n")


if __name__ == "__main__":
    main()