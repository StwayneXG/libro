#!/bin/bash

# Check if a folder name is provided as an argument
if [ $# -eq 0 ]; then
    echo "Usage: $0 <folder_name>"
    exit 1
fi

folder_name="$1"
repos_dir="repos"

# Check if the specified folder exists
if [ ! -d "${repos_dir}/${folder_name}" ]; then
    echo "Error: Folder '${folder_name}' not found in '${repos_dir}' directory."
    exit 1
fi

cd "${repos_dir}"
orgdir=$(pwd)
bname="${folder_name}"

cd "${orgdir}/${bname}"

# setup
git reset --hard HEAD > /dev/null 2>&1
git clean -df > /dev/null 2>&1
git checkout D4J_${bname}_PRE_FIX_REVISION > /dev/null 2>&1
git reset --hard HEAD > /dev/null 2>&1
git clean -df > /dev/null 2>&1
for ncfile in $(git diff D4J_${bname}_BUGGY_VERSION --name-only); do
    if [[ ${ncfile} == *"java"* ]]; then
        continue
    fi
    git checkout D4J_${bname}_BUGGY_VERSION -- ${ncfile} 2> /dev/null
done
defects4j compile 2> /dev/null

# if initially okay, exit
if [[ $? -eq 0 ]]; then
    echo "${bname},ok"
    git commit -m "D4J_${bname}_PRE_FIX_COMPILABLE"
    git tag D4J_${bname}_PRE_FIX_COMPILABLE
    exit 0
fi

# attempt to fix
if [[ ${bname} == *"Jackson"* ]]; then
    for fname in $(git diff D4J_${bname}_BUGGY_VERSION --name-only | grep "PackageVersion"); do
        git checkout D4J_${bname}_BUGGY_VERSION -- ${fname}
    done
fi
if [[ ${bname} == *"Time"* ]] && (( $(ls -1 | wc -l) < 5 )); then
    mv defects4j.build.properties JodaTime
    mv .defects4j.config JodaTime
    cd JodaTime
fi

for fname in $(defects4j compile 2>&1 | grep -o "${bname}/.*\.java.*error" | grep -o "${bname}/.*\.java" | sort -u); do
    git checkout D4J_${bname}_BUGGY_VERSION -- ${fname#*/}
done

# report fix results
defects4j compile > /dev/null 2>&1
if [[ $? -eq 0 ]]; then
    echo "${bname},ok"
    git commit -m "D4J_${bname}_PRE_FIX_COMPILABLE"
    git tag D4J_${bname}_PRE_FIX_COMPILABLE
else
    echo "${bname},fail"
fi