#!/bin/sh

runs=10
for interp in python python3 $@; do
    for proxify in yes no; do
        for expand in yes no; do
            start=$(date +%s)
            for i in $(seq $runs); do 
                $interp pycasonne.py --silent --proxify $proxify --river $expand --inns-cathedrals $expand GeneticAI GeneticAI GeneticAI GeneticAI > /dev/null
            done
            elapsed=$(($(date +%s)-start))
            echo "interp=$($interp -V 2>&1 | tail -n 1), proxify=$proxify, expansions=$expand, elapsed=$elapsed"
        done
    done
done

