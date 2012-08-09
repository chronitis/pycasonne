#!/bin/bash

runs=30
seeds=( )
for i in $(seq $runs); do
    seeds[$i]=$((2<<i))
done
for interp in python python3 $@; do
    for proxify in yes no; do
        for expand in yes no; do
            start=$(date +%s)
            status="success"
            for i in $(seq $runs); do 
                $interp pycasonne.py --silent --proxify $proxify --river $expand --inns-cathedrals $expand --seed ${seeds[$i]} GeneticAI GeneticAI GeneticAI GeneticAI &> /dev/null
                if [ "$?" -gt 0 ]; then
                    status="failed"
                fi
            done
            elapsed=$(($(date +%s)-start))
            average=$(echo "scale=2; $elapsed/$runs" | bc)
            echo "interp=$($interp -V 2>&1 | tail -n 1), proxify=$proxify, expansions=$expand, elapsed=$elapsed, average=$average, status=$status"
        done
    done
done

