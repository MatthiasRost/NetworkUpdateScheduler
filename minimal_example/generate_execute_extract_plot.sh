#!/bin/bash

python -m network_update.cli generate_instances netupdate_example_instances  0 --min_number_nodes 8 --max_number_nodes 12 --min_number_wps 1 --max_number_wps 3 --min_repetition_index 0 --max_repetition_index 3

echo "CREATE BASH SCRIPTS FOR THE EXECUTION USING 2 PROCESSES IN PARALLEL"

python -m network_update.cli write_bash_file_for_parallel_execution execution_netupdate_example_instances.sh netupdate_example_instances.cpickle netupdate_example_sub_process_solutions 2 both both both --timelimit 100 --threads 1 --mip_gap 0.0001 --numeric_focus 2

echo "EXECUTING SCENARIOS IN PARALLEL"

source execution_netupdate_example_instances.sh

echo "MERGING RESULTS"

python -m network_update.cli merge_experiment_storages netupdate_example_solutions_full.cpickle --new_identifier netupdate_example_instances netupdate_example_sub_process_solutions*.cpickle

echo "EXTRACT IMPORTANT DATA"

python -m network_update.cli create_extracted_experiment_data_storage netupdate_example_solutions_full.cpickle netupdate_example_solutions_full_extracted.cpickle


echo "CREATE PLOTS"

mkdir -p ./plots
python -m network_update.cli make_plots_ton_tpc  netupdate_example_solutions_full_extracted.cpickle ./plots/
python -m network_update.cli make_plots_ton_lfru netupdate_example_solutions_full_extracted.cpickle ./plots/

echo "ALL DONE!"
