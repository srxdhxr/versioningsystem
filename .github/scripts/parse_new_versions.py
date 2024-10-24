import sys
import re
import os
def extract_versions(comment):
    # Regex to match the format: step1 | [1.0.0] -> [1.0.1]
    pattern = r'\$\$\$\s*- `(.+?)` \[(.+?)\] -> \[(.+?)\]'
    matches = re.findall(pattern, comment)
    return matches

if __name__ == "__main__":
    comments = os.getenv('LATEST_COMMENT')

    versions = extract_versions(comments)
    for step, current_version, new_version in versions:
        print(f"{step} current version: {current_version} -> new version: {new_version}")
