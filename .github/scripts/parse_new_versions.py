import sys
import re
import os
import subprocess

def extract_versions(comment):
    # Regex to match the format: step1 | [1.0.0] -> [1.0.1]
    pattern = r'\$\$\$\s*- `(.+?)` \[(.+?)\] -> \[(.+?)\]'
    matches = re.findall(pattern, comment)
    return matches

def git_tag_step(step, new_version):
    tag_name = f"{step}-v{new_version}"
    try:
        # Create the tag
        subprocess.run(["git", "tag", tag_name], check=True)
        
        # Push the tag to origin
        subprocess.run(["git", "push", "origin", tag_name], check=True)
        print(f"Successfully tagged {step} with {tag_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error tagging {step} with {tag_name}: {e}", file=sys.stderr)

if __name__ == "__main__":
    comments = os.getenv('LATEST_COMMENT')

    if not comments:
        print("No comment found in environment variable 'LATEST_COMMENT'", file=sys.stderr)
        sys.exit(1)

    versions = extract_versions(comments)
    tag_map = []

    for step, current_version, new_version in versions:
        print(f"{step} current version: {current_version} -> new version: {new_version}")
        tag_map.append(f"{step}:{new_version}")
        
        # Tag the step in git with the new version
        git_tag_step(step, new_version)
    
    tag_str = ",".join(tag_map)
    
    # GitHub Actions requires to output the value in a special format
    print(f"::set-output name=steps_versions::{tag_str}")
