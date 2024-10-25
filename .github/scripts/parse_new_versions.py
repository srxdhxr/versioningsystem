import sys
import re
import os
import json
import subprocess
from typing import List, Tuple
import semver


def extract_versions(comment):
    # Regex to match the format: step1 | [1.0.0] [PATCH|MAJOR|MINOR|x.x.x]
    pattern = r'(.+?) \|\s*\[(.+?)\]\s*\[(.+?)\]'
    matches = re.findall(pattern, comment)

    # Validate the bump type (must be MAJOR, MINOR, PATCH, or a version number)
    valid_bump_types = {'MAJOR', 'MINOR', 'PATCH'}

    parsed_results = []
    for step, current_version, bump_type in matches:
        # If the bump type is not valid, default it to PATCH
        if bump_type not in valid_bump_types and not re.match(r'^\d+\.\d+\.\d+$', bump_type):
            bump_type = 'PATCH'
        
        parsed_results.append((step.strip(), current_version.strip(), bump_type.strip()))
    
    return parsed_results

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


def increment_version(current_version: str, change_type: str) -> str:
    """
    Increment the version based on the change type
    """
    version = semver.VersionInfo.parse(current_version)
    
    if change_type == 'MAJOR':
        return str(version.bump_major())
    elif change_type == 'MINOR':
        return str(version.bump_minor())
    elif change_type == 'PATCH':
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


if __name__ == "__main__":
    comments = os.getenv('LATEST_COMMENT')
    github_token = os.environ.get('GITHUB_TOKEN')
    repository = os.environ.get('GITHUB_REPOSITORY') 

    if not all([github_token, repository, comments]):
        print("No comment found in environment variable 'LATEST_COMMENT'", file=sys.stderr)
        sys.exit(1)

    # Configure git
    configure_git()
    

    versions = extract_versions(comments)
    tag_map = []

    for step, current_version, bump_type in versions:
        print(f"\nProcessing: Step={step}, Change Type={bump_type}")
        
        try:
            # Get current version
            print(f"Current version: {current_version}")
            
            # Calculate new version
            new_version = increment_version(current_version, bump_type)
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

