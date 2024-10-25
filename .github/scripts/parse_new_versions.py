import sys
import re
import os
import json

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

if __name__ == "__main__":
    comments = os.getenv('LATEST_COMMENT')

    if not comments:
        print("No comment found in environment variable 'LATEST_COMMENT'", file=sys.stderr)
        sys.exit(1)

    versions = extract_versions(comments)
    tag_map = []

    for step, current_version, bump_type in versions:
        print(f"{step} current version: {current_version}, bump type: {bump_type}")
        tag_map.append([step, bump_type])
    
    # Output as a JSON string
    tag_json = json.dumps(tag_map)
    
    print(f"INFO: Tag parsed\n {tag_json}")
