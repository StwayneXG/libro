import json
import os
from functools import reduce
from itertools import zip_longest


def get_project_bug(filename):
    # Remove the extension
    filename = filename.split(".")[0]
    parts = filename.split("_")

    if len(parts) >= 2:
        return parts[0], int(parts[1])
    return None, None

def process_json_files(directory_path):
    """Process the JSON files in the specified directory."""
    json_files = [f for f in os.listdir(directory_path) if f.endswith('.json')]

    successful_projects = set()
    success_details = dict()

    for json_file in json_files:
        json_file_path = os.path.join(directory_path, json_file)
        project, bug_number = get_project_bug(json_file)
        success_tests = []
        with open(json_file_path) as f:
            data = json.load(f)

            for filename, info in data.items():
                try:
                    if 'success' in info and info['success'] == True:
                        success_tests.append(filename)
                        successful_projects.add(f"{project}-{bug_number}")
                except:
                    pass
            
            success_details[f"{project}-{bug_number}"] = success_tests

    return successful_projects, success_details

def analyze_project_success(success_projects):
    project_success_details = dict()
    for project in success_projects:
        project_name = project.rsplit('-', 1)[0]
        if project not in project_success_details:
            project_success_details[project] = [project_name]
        else:
            project_success_details[project].append(project_name)
    
    # Change the values to length of the list
    project_success_details = {k: len(v) for k, v in project_success_details.items()}
    return project_success_details

def process_multiple_folders(folders):
    """Process multiple folders and show results separately."""
    for folder in folders:
        print(f"Processing folder: {folder}")

        (success_projects, success_details) = process_json_files(folder)
        project_success_details = analyze_project_success(success_projects)

        print(f"Successful projects: {len(success_projects)}")
        print(f"Project success details: {project_success_details}")


if __name__ == '__main__':
    folders = [f"ghrb/{f}" for f in os.listdir('ghrb') if os.path.isdir(f'ghrb/{f}')]
    process_multiple_folders(folders)