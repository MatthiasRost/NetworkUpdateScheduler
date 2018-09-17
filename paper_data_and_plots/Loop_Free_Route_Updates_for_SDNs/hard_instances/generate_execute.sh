#!/bin/bash

echo "Generating instance storage from the txt files in folger hard_instances_raw..."

python -m network_update.cli create_instance_storage_for_hard_instances hard_instances_8_512.cpickle hard_instances_raw/8.txt hard_instances_raw/16.txt hard_instances_raw/32.txt hard_instances_raw/64.txt hard_instances_raw/128.txt hard_instances_raw/256.txt hard_instances_raw/512.txt

echo "Write execution file"

python -m network_update.cli write_bash_file_for_parallel_execution execute_hard.sh hard_instances.cpickle results_hard_instances_ 7 no no no --timelimit 86400 --threads 4 --mip_gap 0.0001 --numeric_focus 2

echo "Execute.."
echo "Running the script will use 28 many Threads. Be sure that you want this.. Aborting.."

exit 0

source execute_hard.sh

Echo "Merge experiment storages"

python -m network_update.cli merge_experiment_storages results_hard_instances_8_512.cpickle results_hard_instances_*_7.cpickle




