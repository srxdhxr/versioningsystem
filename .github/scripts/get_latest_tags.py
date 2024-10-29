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
    
    Example tags:
    step1-v1.0.0
    step1-v1.1.0
    step2-v0.1.0
    
    Would return: [["step1", "1.1.0"], ["step2", "0.1.0"]]
    """
    # Fetch latest main branch
    _, stderr, return_code = run_command(['git', 'fetch', 'origin', 'main'])
    if return_code != 0:
        print(f"Error fetching main branch: {stderr}")
        return []
        
    # Get the commit hash of the main branch
    stdout, stderr, return_code = run_command(['git', 'rev-parse', 'origin/main'])
    if return_code != 0:
        print(f"Error getting main branch commit: {stderr}")
        return []
    main_commit = stdout.strip()
    
    # Get all tags that point to commits in main branch history
    stdout, stderr, return_code = run_command(['git', 'tag', '--contains', main_commit])
    if return_code != 0:
        print(f"Error getting tags: {stderr}")
        return []
    print("Here")

    if not stdout:
        return []

    step_versions = {}
    for tag in stdout.split('\n'):
        print(f"Processing tag: {tag}")
        # Skip empty tags
        if not tag:
            continue
            
        # Look for tags in the format "stepname-vX.Y.Z"
        if not tag.count("-v") == 1:
            print(f"Skipping tag with invalid format: {tag}")
            continue
            
        try:
            # Split on last occurrence of "-v" to handle stepnames that might contain "-v"
            stepname, version = tag.rsplit("-v", 1)
            
            # Validate version with semver
            parsed_version = semver.VersionInfo.parse(version)
            
            # Verify tag is on main branch
            _, stderr, return_code = run_command(['git', 'merge-base', '--is-ancestor', f'{tag}^{{commit}}', 'origin/main'])
            if return_code != 0:
                print(f"Skipping tag not in main branch history: {tag}")
                continue
            
            if stepname in step_versions:
                current_version = step_versions[stepname][1]  # Get the version string
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

    # Convert the dictionary to a sorted list of lists
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