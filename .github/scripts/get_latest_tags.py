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


import semver
from typing import List

def get_step_versions() -> List[List[str]]:
    """
    Get the latest version for each step in the repository.
    Returns a list of lists in the format [[stepname, version]].
    """
    stdout, _, _ = run_command(['git', 'tag', '-l'])
    if not stdout:
        return []

    step_versions = {}
    for tag in stdout.split('\n'):
        # Look for tags in the format "stepname-vX.Y.Z"
        if "-v" in tag:
            try:
                # Extract stepname and versio
                stepname, version = tag.rsplit("-v", 1)
                semver.VersionInfo.parse(version) 
                if stepname in step_versions:
                    # Update
                    current_version = step_versions[stepname]
                    if semver.VersionInfo.parse(version) > semver.VersionInfo.parse(current_version):
                        step_versions[stepname] = version
                else:
                    step_versions[stepname] = version
            except ValueError:
                continue  
    # Convert the dictionary to a list of lists
    return [[step, version] for step, version in step_versions.items()]




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

    if not all([github_token, repository]):
        print("Missing required environment variables")
        sys.exit(1)
    
    # Configure git
    configure_git()

    tag_map = get_step_versions()
    
    tag_json = json.dumps(tag_map)
    print(f"INFO: tag_map = \n{tag_json}")
    with open(os.environ['GITHUB_ENV'], 'a') as env_file:
        env_file.write(f"TAG_MAP={tag_json}\n")

if __name__ == "__main__":
    main()