#!/bin/bash

echo "This script exists to show the commands used for our evaluation."
echo "Executing this script -- including the generated bash scripts for executing the instances using 40 processes -- will probably overload your system."
echo "Accordingly, think twice. Aborting exceution..."

exit 1

echo "GENERATE INSTANCES"

python -m network_update.cli generate_instances instances_ton_N_15-35_W_1-5_I_0-99  0 --min_number_nodes 15 --max_number_nodes 35 --min_number_wps 1 --max_number_wps 5 --min_repetition_index 0 --max_repetition_index 99

python -m network_update.cli generate_additional_instances instances_ton_N_15-35_W_1-5_I_100-199  0 --min_number_nodes 15 --max_number_nodes 35 --min_number_wps 1 --max_number_wps 5 --min_repetition_index 100 --max_repetition_index 199 instances_ton_N_15-35_W_1-5_I_0-99.cpickle

python -m network_update.cli generate_additional_instances instances_ton_N_15-35_W_1-5_I_200-249  0 --min_number_nodes 15 --max_number_nodes 35 --min_number_wps 1 --max_number_wps 5 --min_repetition_index 200 --max_repetition_index 249 instances_ton_N_15-35_W_1-5_I_0-99.cpickle instances_ton_N_15-35_W_1-5_I_100-199.cpickle


echo "MERGE INSTANCE STORAGES"

python -m network_update.cli merge_instance_storages instances_ton_N_15-35_W_1-5_I_0-249.cpickle  instances_ton_N_15-35_W_1-5_I_0-99.cpickle instances_ton_N_15-35_W_1-5_I_100-199.cpickle instances_ton_N_15-35_W_1-5_I_200-249.cpickle


echo "CREATE BASH SCRIPTS FOR THE EXECUTION USING 40 PROCESSES IN PARALLEL"

python -m network_update.cli write_bash_file_for_parallel_execution execution_ton_0-99_script.sh instances_ton_N_15-35_W_1-5_I_0-99.cpickle solutions_instances_ton_N_15-35_W_1-5_I_0-99 40 both both both --timelimit 1000 --threads 1 --mip_gap 0.0001 --numeric_focus 2

python -m network_update.cli write_bash_file_for_parallel_execution execution_ton_100-199_script.sh instances_ton_N_15-35_W_1-5_I_100-199.cpickle solutions_instances_ton_N_15-35_W_1-5_I_100-199 40 both both both --timelimit 1000 --threads 1 --mip_gap 0.0001 --numeric_focus 2

python -m network_update.cli write_bash_file_for_parallel_execution execution_ton_200-249_script.sh instances_ton_N_15-35_W_1-5_I_200-249.cpickle solutions_instances_ton_N_15-35_W_1-5_I_200-249 40 both both both --timelimit 1000 --threads 1 --mip_gap 0.0001 --numeric_focus 2

echo "EXECUTE SCRIPTS USING UP TO 40 PROCESSES"
echo "YOU PROBABLY DON'T WANT TO DO THIS AND THE SCRIPT IS ABORTING NOW!"
exit 1

source execution_ton_0-99_script.sh
source execution_ton_100-199_script.sh
source execution_ton_200_299_script.sh

echo "MERGING RESULTS"

python -m network_update.cli merge_experiment_storages solutions_ton_N_15-35_W_1-5_I_0-249.cpickle --new_identifier solutions_ton_N_15-35_W_1-5_I_0-249 solutions_instances_ton_*.cpickle

echo "EXTRACT IMPORTANT DATA"

python -m network_update.cli create_extracted_experiment_data_storage solutions_ton_N_15-35_W_1-5_I_0-249.cpickle solutions_ton_N_15-35_W_1-5_I_0-249_extracted_data.cpickle

echo "PLOT DATA"

python -m network_update.cli make_plots_ton_tpc solutions_ton_N_15-35_W_1-5_I_0-249_extracted_data.cpickle ./plots/

ECHO "ALL DONE!"
