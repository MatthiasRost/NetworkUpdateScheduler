#!/bin/bash

echo "This script exists to show the commands used for our evaluation."
echo "Executing this script -- including the generated bash scripts for executing the instances using 40 processes -- will probably overload your system."
echo "Accordingly, think twice. Aborting exceution..."

exit 1

echo "GENERATE INSTANCES"

python $PYTHONPATH/cli.py generate_instances ton_2018_netupdate_instances_0_99  0 --min_number_nodes 15 --max_number_nodes 35 --min_number_wps 1 --max_number_wps 5 --min_repetition_index 0 --max_repetition_index 99

python $PYTHONPATH/cli.py generate_additional_instances ton_2018_netupdate_instances_100_199  0 --min_number_nodes 15 --max_number_nodes 35 --min_number_wps 1 --max_number_wps 5 --min_repetition_index 100 --max_repetition_index 199 ton_2018_netupdate_instances_0_99.cpickle

python $PYTHONPATH/cli.py generate_additional_instances ton_2018_netupdate_instances_200_249  0 --min_number_nodes 15 --max_number_nodes 35 --min_number_wps 1 --max_number_wps 5 --min_repetition_index 200 --max_repetition_index 249 ton_2018_netupdate_instances_0_99.cpickle ton_2018_netupdate_instances_100_199.cpickle


echo "MERGE INSTANCE STORAGES"

python $PYTHONPATH/cli.py merge_instance_storages ton_2018_netupdate_instances.cpickle ton_2018_netupdate_instances ton_2018_netupdate_instances_0_99.cpickle ton_2018_netupdate_instances_100_199.cpickle ton_2018_netupdate_instances_200_249.cpickle


echo "CREATE BASH SCRIPTS FOR THE EXECUTION USING 40 PROCESSES IN PARALLEL"

python $PYTHONPATH/cli.py write_bash_file_for_parallel_execution execution_ton_0_99_script.sh ton_2018_netupdate_instances_0_99.cpickle results_ton_2018_netupdate_instances_0_99 40 both both both --timelimit 1000 --threads 1 --mip_gap 0.0001 --numeric_focus 2

python $PYTHONPATH/cli.py write_bash_file_for_parallel_execution execution_ton_100_199_script.sh ton_2018_netupdate_instances_100_199.cpickle results_ton_2018_netupdate_instances_100_199 40 both both both --timelimit 1000 --threads 1 --mip_gap 0.0001 --numeric_focus 2

python $PYTHONPATH/cli.py write_bash_file_for_parallel_execution execution_ton_200_249_script.sh ton_2018_netupdate_instances_200_249.cpickle results_ton_2018_netupdate_instances_200_249 40 both both both --timelimit 1000 --threads 1 --mip_gap 0.0001 --numeric_focus 2

echo "EXECUTE SCRIPTS USING UP TO 120 PROCESSES"
echo "YOU PROBABLY DON'T WANT TO DO THIS AND THE SCRIPT IS ABORTING NOW!"
exit 1

./execution_ton_0_99_script.sh
./execution_ton_100_199_script.sh
./execution_ton_200_299_script.sh

echo "MERGING RESULTS"

python $PYTHONPATH/cli.py merge_experiment_storages ton_2018_netupdate_solution_storage.cpickle --new_identifier ton_2018_netupdate_instances results_ton_*.cpickle

echo "EXTRACT IMPORTANT DATA"

python $PYTHONPATH/cli.py create_extracted_experiment_data_storage ton_2018_netupdate_solution_storage.cpickle ton_2018_netupdate_solution_storage_extracted_data.cpickle

ECHO "ALL DONE!"
