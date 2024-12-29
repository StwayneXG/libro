#!/bin/bash

cdir=$(pwd)
D4J_HOME="$(dirname $(which defects4j))/../../"
MAX_JOBS=8

process_bug() {
    local proj=$1
    local bug=$2
    experiment_name="gpt-4o_openbook_rephrased"

    # # If /root/results/hashmask/{proj}_{bug}.json exists, skip this bug
    # if [ -f "/root/results/${experiment_name}/${proj}_${bug}.json" ]; then
    #     return
    # fi

    # If there is no txt file by the format {proj}_{bug}_n*.txt in the folder /root/data/Defects4J/gen_tests/{experiment_name}/, skip this bug
    if [ ! -f "/root/data/Defects4J/gen_tests/${experiment_name}/${proj}_${bug}_n0.txt" ]; then
        return
    fi

    defects4j checkout -p $proj -v ${bug}b -w /root/data/Defects4J/repos/${proj}_${bug}
    cd /root/data/Defects4J/
    bash /root/data/Defects4J/tag_pre_fix_compilable_single.sh ${proj}_${bug}
    bash /root/data/Defects4J/tag_post_fix_compilable_single.sh ${proj}_${bug}
    cd $cdir
    python3.9 postprocess_d4j.py -p $proj -b $bug --experiment_name $experiment_name
    rm -rf /root/data/Defects4J/repos/${proj}_${bug}
}

for proj in $(defects4j pids); do
    for bug in $(cut -f1 -d',' "$D4J_HOME/framework/projects/$proj/commit-db"); do

#        if [ "$proj" != "Time" ]; then
#            continue
#        fi
#        if [ "$bug" != "14" ]; then
#            continue
#        fi

        # Wait if we've reached the maximum number of parallel jobs
        while [ $(jobs -r | wc -l) -ge $MAX_JOBS ]; do
            sleep 1
        done

        # Start a new job in the background
        process_bug $proj $bug &

        # Optionally, you can add a small delay to prevent potential race conditions
        sleep 0.1
        # break
    done
    # break
done

# Wait for all background jobs to finish
wait

echo "All jobs completed."