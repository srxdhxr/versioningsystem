import os
import sys
import json
import requests
from typing import List, Tuple

def get_docker_tags(username: str, folders: List[str], token: str) -> List[Tuple[str, str]]:
    """
    Get latest tags for given folders from Docker Hub
    
    Args:
        username: Docker Hub username
        folders: List of folder/image names to check
        token: Docker Hub token
    
    Returns:
        List of tuples containing (image_name, latest_tag)
    """
    results = []
    headers = {'Authorization': f'Bearer {token}'}
    
    for folder in folders:
        if not folder:  # Skip empty folder names
            continue
            
        # Construct API URL for tags
        url = f'https://hub.docker.com/v2/repositories/{username}/{folder}/tags'
        params = {'page_size': 1, 'ordering': 'last_updated'}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('results'):
                latest_tag = data['results'][0]['name']
                results.append([folder, latest_tag])
                print(f"Found tag for {folder}: {latest_tag}", file=sys.stderr)
            else:
                print(f"No tags found for {folder}", file=sys.stderr)
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching tags for {folder}: {str(e)}", file=sys.stderr)
            continue
    
    return results

def main():
    """
    Main function to process input and return results
    Expects JSON array of folders as first argument
    Expects Docker username as second argument
    Expects Docker token as third argument
    """
    if len(sys.argv) != 4:
        print("Usage: script.py '[folders]' username token", file=sys.stderr)
        sys.exit(1)
    
    try:
        folders = json.loads(sys.argv[1])
        username = sys.argv[2]
        token = sys.argv[3]
        
        if not isinstance(folders, list):
            raise ValueError("Input must be a JSON array")
            
        results = get_docker_tags(username, folders, token)
        
        # Print results as JSON array
        print(json.dumps(results))
        
    except json.JSONDecodeError as e:
        print(f"Error parsing input JSON: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()