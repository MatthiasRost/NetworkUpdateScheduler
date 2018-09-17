#!/bin/bash

echo "This script exists to show the commands used for our evaluation."
echo "Executing this script -- including the generated bash scripts for executing the instances using 40 processes -- will probably overload your system."
echo "Accordingly, think twice. Aborting exceution..."

exit 1

echo "GENERATE INSTANCES"

python -m network_update.cli generate_instances instances_10_60_0_500  0 --min_number_nodes 10 --max_number_nodes 60 --min_number_wps 0 --max_number_wps 0 --min_repetition_index 0 --max_repetition_index 499

echo "CREATE BASH SCRIPTS FOR THE EXECUTION USING 40 PROCESSES IN PARALLEL"

python -m network_update.cli write_bash_file_for_parallel_execution execute_instances_10_60_0_500.sh instances_10_60_0_500.cpickle solutions_instances_10_60_0_500 40 no both no --timelimit 1800 --threads 1 --mip_gap 0.0001 --numeric_focus 2

echo "EXECUTE SCRIPTS USING UP TO 40 PROCESSES"
echo "YOU PROBABLY DON'T WANT TO DO THIS AND THE SCRIPT IS ABORTING NOW!"
exit 1

source execute_instances_10_60_0_500.sh

echo "MERGING RESULTS"

python -m network_update.cli merge_experiment_storages results_instances_10_60_0_500_aggregated.cpickle solutions_instances_10_60_0_500*.cpickle

echo "EXTRACT IMPORTANT DATA"

python -m network_update.cli create_extracted_experiment_data_storage results_instances_10_60_0_500_extracted results_instances_10_60_0_500_aggregated.cpickle

echo "PLOT DATA"

python -m network_update.cli make_plots_ton_lfru results_instances_10_60_0_500_extracted.cpickle ./plots/

ECHO "ALL DONE!"
