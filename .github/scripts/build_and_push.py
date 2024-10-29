import docker
import json
import subprocess
import sys
import semver
from typing import List, Tuple
from pathlib import Path
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



def image_exists_locally(client, full_image_name: str) -> bool:
    """Check if a Docker image exists locally."""
    try:
        image = client.images.get(full_image_name)
        print(f"Image {full_image_name} found locally.")
        return True
    except docker.errors.ImageNotFound:
        return False


def build_and_push(
    path: str,
    project: str,
    version: str,
    registry: str = "docker.cloud.reveliolabs.com:5000",
    quiet: bool = False,
    user = 'foo',
    pwd = ''
):
    client = docker.from_env()
    full_image_name = f"{registry}/{project}:{version}"

    if image_exists_locally(client, full_image_name):
        print(f"Image {full_image_name} already exists. Skipping build.")
    else:
        if user != 'foo':
            client.login(username=user,password = pwd)
        else:
            client.login(username=user, registry=registry)

        print(f"Starting build for {project}, version: {version}")
        print("Running docker build at path: %s", path)
        # Should raise 3an error if failed
        try:
            _, logs = client.images.build(
                path=path,
                tag=f"{registry}/{project}:{version}",
                quiet=quiet,
                nocache=False,
            )
            for log_line in logs:
               print(log_line)

        except BuildError as e:
            print("Something went wrong with image build!")
            for line in e.build_log:
                if "stream" in line:
                    print(line["stream"].strip())
            raise e

        push_resp = client.images.push(
            f"{registry}/{project}",
            tag=version,
            stream=True,
            decode=True,
        )
        for line in push_resp:
            print(line)
            if line.get("error"):
                raise RuntimeError("Push failed!")


def process_tag_map(tag_map_str: str) -> List[Tuple[str, str]]:
    """
    Process the tag map JSON string into a list of tuples.
    
    Args:
        tag_map_str: JSON string in format [[step, version], ...]
        
    Returns:
        List of (step, version) tuples
    """
    try:
        tag_map = json.loads(tag_map_str)
        return [(item[0], item[1]) for item in tag_map]
    except json.JSONDecodeError as e:
        print(f"Failed to parse tag map JSON: {e}")
        raise
    except (IndexError, TypeError) as e:
        print(f"Invalid tag map format: {e}")
        raise

    
def main():
    
    # Get environment variables
    github_token = os.environ.get('GITHUB_TOKEN')
    repository = os.environ.get('GITHUB_REPOSITORY')
    project_dir = os.environ.get('PROJECT_DIR')
    registry = os.environ.get('REGISTRY')
    user = os.environ.get('DOCKER_USER')
    pwd = os.environ.get('DOCKER_PWD')

    if not all([github_token, repository,project_dir,registry]):
        print("Missing required environment variables")
        sys.exit(1)



    try:
        
        # Process tag map
        steps = get_step_versions()
        print(f"Processing {len(steps)} steps")
        
        # Track results
        results = []
        
        # Process each step
        for step_name, version in steps:
            step_path = Path(project_dir) / step_name
            
            
            success = build_and_push(
                path=str(step_path),
                project=step_name,
                version=version,
                registry=registry,
                user = user,
                pwd = pwd
            )
            
            results.append((step_name, version, success))
        
        # Print summary
        print("\nBuild Summary:")
        all_successful = True
        for step_name, version, success in results:
            status = "✓ Success" if success else "✗ Failed"
            print(f"{status}: {step_name}:{version}")
            all_successful = all_successful and success
        
        if not all_successful:
            sys.exit(1)
            
    except Exception as e:
        print(f"Script failed: {str(e)}")
        sys.exit(1)
    


if __name__ == "__main__":
    main()
