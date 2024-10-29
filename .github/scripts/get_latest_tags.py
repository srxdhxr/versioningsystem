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

def get_step_versions() -> List[List[str]]:
    """
    Get the latest version for each step from the main branch.
    Returns a list of lists in the format [[stepname, version]].
    """
    # Debug: Print all tags first
    stdout, stderr, return_code = run_command(['git', 'tag', '-l'])
    print(f"DEBUG: Initial tags in repository:\n{stdout}")
    
    # Fetch latest main branch and tags
    print("Fetching latest main branch and tags...")
    _, stderr, return_code = run_command(['git', 'fetch', '--tags', 'origin', 'main'])
    if return_code != 0:
        print(f"Error fetching main branch: {stderr}")
        return []
    
    # Debug: Print tags after fetch
    stdout, stderr, return_code = run_command(['git', 'tag', '-l'])
    print(f"DEBUG: Tags after fetch:\n{stdout}")
        
    # Get the commit hash of the main branch
    stdout, stderr, return_code = run_command(['git', 'rev-parse', 'origin/main'])
    if return_code != 0:
        print(f"Error getting main branch commit: {stderr}")
        return []
    main_commit = stdout.strip()
    print(f"DEBUG: Main branch commit: {main_commit}")
    
    # Get all tags
    stdout, stderr, return_code = run_command(['git', 'tag', '--points-at', main_commit])
    if return_code != 0:
        print(f"Error getting tags: {stderr}")
        return []

    if not stdout:
        print("DEBUG: No tags found pointing to main branch")
        # Fallback to getting all tags
        stdout, stderr, return_code = run_command(['git', 'tag', '-l'])
        if return_code != 0 or not stdout:
            print("DEBUG: No tags found at all")
            return []

    step_versions = {}
    for tag in stdout.split('\n'):
        print(f"Processing tag: {tag}")
        if not tag:
            continue
            
        if not tag.count("-v") == 1:
            print(f"Skipping tag with invalid format: {tag}")
            continue
            
        try:
            stepname, version = tag.rsplit("-v", 1)
            parsed_version = semver.VersionInfo.parse(version)
            
            if stepname in step_versions:
                current_version = step_versions[stepname][1]
                current_parsed = semver.VersionInfo.parse(current_version)
                if parsed_version > current_parsed:
                    print(f"Updating {stepname} from version {current_version} to {version}")
                    step_versions[stepname] = (stepname, version)
            else:
                print(f"Adding new step {stepname} with version {version}")
                step_versions[stepname] = (stepname, version)
                
        except (ValueError, semver.ParseError) as e:
            print(f"Warning: Skipping invalid tag format: {tag} (Error: {str(e)})")
            continue

    result = sorted([[step, version] for step, version in step_versions.values()])
    print(f"Final result: {result}")
    return result

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

    # Get and print tags for debugging
    stdout, _, _ = run_command(['git', 'tag', '-l'])
    print(f"DEBUG: All tags in repository:\n{stdout}")

    tag_map = get_step_versions()
    
    tag_json = json.dumps(tag_map)
    print(f"INFO: tag_map = \n{tag_json}")
    with open(os.environ['GITHUB_ENV'], 'a') as env_file:
        env_file.write(f"TAG_MAP={tag_json}\n")

if __name__ == "__main__":
    main()