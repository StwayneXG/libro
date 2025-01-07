#!/bin/bash

MAX_JOBS=8

# Function to process a bug
process_bug() {
    local proj=$1
    local bug=$2

    # Run the processing command
    python3.9 postprocess_ghrb.py -p $proj -b $bug --exp_name "libro_default"
}

# Function to manage processing for a project
process_project() {
    local proj=$1
    local bugs=("${@:2}")

    for bug in "${bugs[@]}"; do
        # Process the bug and wait for it to complete before starting the next one
        process_bug $proj $bug
    done
}

# Group bugs by project
declare -A project_bugs
while IFS=, read -r proj bug; do
    # Skip the header row
    if [[ "$proj" == "Project" ]]; then
        continue
    fi

    # If proj != google_gson, skip this bug
    # if [ "$proj" == "google_gson" ]; then
    #     continue
    # fi

    # Append the bug to the project's list
    project_bugs["$proj"]+="$bug "
done < /root/data/GHRB/project_ids.csv

# Process each project cluster with global MAX_JOBS limit
for proj in "${!project_bugs[@]}"; do
    # Wait if the total number of parallel jobs exceeds MAX_JOBS
    while [ $(jobs -r | wc -l) -ge $MAX_JOBS ]; do
        sleep 1
    done

    # Convert the space-separated bug list into an array
    bugs=(${project_bugs[$proj]})

    # Start processing the project cluster in the background
    process_project "$proj" "${bugs[@]}" &
done

# Wait for all project clusters to complete
wait

# Log script completion
echo "All jobs completed."