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
            semver.VersionInfo.parse(version)
            versions.append(version)
        except ValueError:
            continue
    
    if not versions:
        return '1.0.0'
    
    return str(max(versions, key=semver.VersionInfo.parse))

def increment_version(current_version: str, change_type: str) -> str:
    """
    Increment the version based on the change type
    """
    version = semver.VersionInfo.parse(current_version)
    
    if change_type == 'major':
        return str(version.bump_major())
    elif change_type == 'minor':
        return str(version.bump_minor())
    elif change_type == 'patch':
        return str(version.bump_patch())
    else:
        raise ValueError(f"Invalid change type: {change_type}")

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

def create_and_push_tag(step: str, version: str, github_token: str, repository: str) -> bool:
    """
    Create and push a new tag for the given step and version
    """
    tag_name = f"{step}-v{version}"
    
    # Set the remote URL with authentication
    remote_url = f"https://x-access-token:{github_token}@github.com/{repository}.git"
    _, stderr, code = run_command(['git', 'remote', 'set-url', 'origin', remote_url])
    if code != 0:
        print(f"Failed to set remote URL: {stderr}")
        return False
    
    # Delete tag if it exists locally
    run_command(['git', 'tag', '-d', tag_name])
    
    # Create new tag
    _, stderr, code = run_command(['git', 'tag', tag_name])
    if code != 0:
        print(f"Failed to create tag: {stderr}")
        return False
    
    # Push tag to remote
    _, stderr, code = run_command(['git', 'push', 'origin', tag_name, '--force'])
    if code != 0:
        print(f"Failed to push tag: {stderr}")
        return False
    
    return True

def main():
    # Get environment variables
    github_token = os.environ.get('GITHUB_TOKEN')
    repository = os.environ.get('GITHUB_REPOSITORY')
    steps_versions = os.environ.get('STEPS_VERSIONS')
    
    if not all([github_token, repository, steps_versions]):
        print("Missing required environment variables")
        sys.exit(1)
    
    # Configure git
    configure_git()
    
    try:
        changes = json.loads(steps_versions)
    except json.JSONDecodeError as e:
        print(f"Failed to parse STEPS_VERSIONS JSON: {e}")
        print(f"Received content: {steps_versions}")
        sys.exit(1)
    
    # Process each change
    for step, change_type in changes:
        print(f"\nProcessing: Step={step}, Change Type={change_type}")
        
        try:
            # Get current version
            current_version = get_current_version(step)
            print(f"Current version: {current_version}")
            
            # Calculate new version
            new_version = increment_version(current_version, change_type)
            print(f"New version: {new_version}")
            
            # Create and push tag
            if create_and_push_tag(step, new_version, github_token, repository):
                print(f"✅ Successfully created and pushed tag for {step}-v{new_version}")
            else:
                print(f"❌ Failed to create/push tag for {step}")
                sys.exit(1)
                
        except Exception as e:
            print(f"Error processing {step}: {str(e)}")
            sys.exit(1)
    
    # List all tags at the end
    stdout, _, _ = run_command(['git', 'tag', '-l'])
    print("\nFinal list of tags:")
    print(stdout)

if __name__ == "__main__":
    main()