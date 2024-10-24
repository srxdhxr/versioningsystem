import sys
import re
import os
import json

def extract_versions(comment):
    # Regex to match the format: step1 | [1.0.0] -> [1.0.1]
    pattern = r'\$\$\$\s*- `(.+?)` \[(.+?)\] -> \[(.+?)\]'
    matches = re.findall(pattern, comment)
    return matches

if __name__ == "__main__":
    comments = os.getenv('LATEST_COMMENT')

    if not comments:
        print("No comment found in environment variable 'LATEST_COMMENT'", file=sys.stderr)
        sys.exit(1)

    versions = extract_versions(comments)
    tag_map = []

    for step, current_version, new_version in versions:
        print(f"{step} current version: {current_version} -> new version: {new_version}")
        tag_map.append([step, new_version])
    
    # Output as a JSON string
    tag_json = json.dumps(tag_map)
    print(f"::set-output name=steps_versions::{tag_json}")
