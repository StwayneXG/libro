import json
import os
from functools import reduce
from itertools import zip_longest

# Defining the mapping of projects to their maximum bug numbers for defects4j v1
defects4j_v1_criteria = {
    "Chart": 26,
    "Closure": 133,
    "Lang": 65,
    "Math": 106,
    "Mockito": 38,
    "Time": 27
}

def is_defects4j_v1(project, bug_number):
    """Check if the given project and bug number belong to defects4j v1."""
    return bug_number <= defects4j_v1_criteria.get(project, 0)

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

    success_projects_v1 = set()
    success_projects_v2 = set()

    success_details_v1 = dict()
    success_details_v2 = dict()

    total_projects_v1 = 0
    total_projects_v2 = 0

    total_tests_v1 = 0
    total_tests_v2 = 0

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
                except:
                    pass

        if is_defects4j_v1(project, bug_number):
            total_projects_v1 += 1
            total_tests_v1 += len(data)
        else:
            total_projects_v2 += 1
            total_tests_v2 += len(data)

        if len(success_tests) > 0:
            project_bug = json_file.split(".")[0]
            if is_defects4j_v1(project, bug_number):
                success_projects_v1.add(project_bug)
                success_details_v1[project_bug] = success_tests
            else:
                success_projects_v2.add(project_bug)
                success_details_v2[project_bug] = success_tests

    return success_projects_v1, success_projects_v2, success_details_v1, success_details_v2, total_projects_v1, total_projects_v2, total_tests_v1, total_tests_v2

def print_summary(success_projects_v1, success_projects_v2,
                    success_details_v1, success_details_v2,
                    total_projects_v1, total_projects_v2,
                    total_tests_v1, total_tests_v2):
    """Print the summary of the results."""
    print('Defects4J v1:')
    print(f'Successful projects: {len(success_projects_v1)}/{total_projects_v1}')
    print(f'Successful tests: {sum(len(v) for v in success_details_v1.values() if v is not None)}/{total_tests_v1}')
    print()

    print('Defects4J v2:')
    print(f'Successful projects: {len(success_projects_v2)}/{total_projects_v2}')
    print(f'Successful tests: {sum(len(v) for v in success_details_v2.values() if v is not None)}/{total_tests_v2}')
    print()

    full_success_projects = success_projects_v1.union(success_projects_v2)
    full_success_details = success_details_v1 | success_details_v2
    print('Complete Defects4J:')
    print(f'Successful projects: {len(full_success_projects)}/{total_projects_v1 + total_projects_v2}')
    print(f'Successful tests: {sum(len(v) for v in full_success_details.values() if v is not None)}/{total_tests_v1 + total_tests_v2}')
    print()

def print_projects_in_columns(title, projects, num_columns=4):
    """Print a set of projects in multiple columns."""
    projects = sorted(projects)
    num_projects = len(projects)
    rows = (num_projects + num_columns - 1) // num_columns
    columns = [projects[i * rows:(i + 1) * rows] for i in range(num_columns)]

    print(f"{title} (Total: {num_projects}):")
    for row in zip_longest(*columns, fillvalue=""):
        print(" | ".join(f"{project:<30}" for project in row))
    print()

def print_unique_projects_with_counts(title, unique_projects, success_details, num_columns=4):
    """Print unique projects with their success counts in multiple columns."""
    unique_projects_with_counts = [(proj, len(success_details[proj])) for proj in sorted(unique_projects)]
    num_unique_projects = len(unique_projects_with_counts)
    rows = (num_unique_projects + num_columns - 1) // num_columns
    columns = [unique_projects_with_counts[i * rows:(i + 1) * rows] for i in range(num_columns)]

    print(f"{title} (Total: {num_unique_projects}):")
    for row in zip_longest(*columns, fillvalue=("","")):
        print(" | ".join(f"{proj:<20} ({count:>3})" for proj, count in row))
    print()

def compare_folders(results):
    """Find the common and unique projects in the specified folders."""
    folder_names = list(results.keys())

    # Extract project sets for each folder
    projects_in_folders = {
        folder: set(results[folder][0]).union(set(results[folder][1]))
        for folder in folder_names
    }

    # Find common projects across all folders
    common_projects = reduce(lambda x, y: x & y, projects_in_folders.values())
    print_projects_in_columns("Common projects in all folders", common_projects)

    # Find unique projects for each folder
    for i in range(len(folder_names)):
        unique_projects = projects_in_folders[folder_names[i]].copy()
        for j in range(len(folder_names)):
            if i != j:
                unique_projects -= projects_in_folders[folder_names[j]]
        success_details = {**results[folder_names[i]][2], **results[folder_names[i]][3]}
        print_unique_projects_with_counts(f"Projects unique to {folder_names[i]}", unique_projects, success_details)

    # Find common projects between pairs of folders
    for i in range(len(folder_names)):
        for j in range(i + 1, len(folder_names)):
            common_in_pair = projects_in_folders[folder_names[i]] & projects_in_folders[folder_names[j]]
            print_projects_in_columns(f"Common projects in {folder_names[i]} and {folder_names[j]}", common_in_pair)

def process_multiple_folders(folders, compare_folders_flag=False):
    """Process multiple folders and show results separately."""
    results = dict()
    for folder in folders:
        print(f"Processing folder: {folder}")

        (success_projects_v1, success_projects_v2,
         success_details_v1, success_details_v2,
         total_projects_v1, total_projects_v2,
         total_tests_v1, total_tests_v2) = process_json_files(folder)

        results[folder] = (success_projects_v1, success_projects_v2,
                            success_details_v1, success_details_v2,
                            total_projects_v1, total_projects_v2,
                            total_tests_v1, total_tests_v2)

        print_summary(success_projects_v1, success_projects_v2,
                        success_details_v1, success_details_v2,
                        total_projects_v1, total_projects_v2,
                        total_tests_v1, total_tests_v2)

        print("\n" + "-"*40 + "\n")

    if len(folders) > 1 and compare_folders_flag:
        compare_folders(results)

if __name__ == '__main__':
    folders = [f for f in os.listdir() if os.path.isdir(f)]
    process_multiple_folders(folders, compare_folders_flag=False)