
# Overview

This repository contains algorithms and a simulation framework to schedule **loop-free network** updates that can also
take **waypoints**  into account.

The code is written in **Python2.7** and requires some few packages, most notable **Gurobi**, a commercial Mixed-Integer Programming solver, which is free for academic use. 

The code has been the basis for computational evaluations within the following publications:

**[1]** Klaus-Tycho Foerster, Arne Ludwig, Jan Marcinkowski, and Stefan Schmid: **"Loop-Free Route Updates for Software-Defined Networks"**. IEEE/ACM Transactions on Networking (TON), 2018.

**[2]** Arne Ludwig, Szymon Dudycz, Matthias Rost, and Stefan Schmid: **"Transiently Secure Network Updates"**. 42nd ACM SIGMETRICS, Antibes Juan-les-Pins, France, June 2016.

**[3]** Arne Ludwig, Matthias Rost, Damien Foucard, and Stefan Schmid: **"Good Network Updates for Bad Packets: Waypoint Enforcement Beyond Destination-Based Routing Policies"**. 13th ACM Workshop on Hot Topics in Networks (HotNets), Los Angeles, California, USA, October 2014.

# Code Struture

The code is structured as follows:

 * **datamodel.py** contains all structures to store (and generate) network update instances and their solution.
 * **experiment_execution.py** contains the code to execute slices of instances.
 * **gurobi_interface.py** contains the different MIP formulations for solving the network update instances (see paper [2]).
 * **postprocess_solutions.py** allows to extract the most important data from the solution.
 * **cli.py** provides the command-line interface to generate, execute and evaluate the experiments (see below).

# Using the Code

## Generation of Instances

In the following we shortly outline how the command-line interface can be used to generate and execute some instances. 
Our examples are based on our most recent submission to the **IEEE/ACM journal Transactions on Networking**.

The following commands were used to create 3 different instance storages containing 100, 100 and 50 instances for node numbers
ranging from 15 to 35 and waypoints ranging from 1 to 5. To only generate unique instances (and not draw the same instance) multiple times,
the previously generated instance containers should be passed to the **generate_additonal_instances** function.

```
python $PYTHONPATH/cli.py generate_instances ton_2018_netupdate_instances_0_99  0 --min_number_nodes 15 --max_number_nodes 35 --min_number_wps 1 --max_number_wps 5 --min_repetition_index 0 --max_repetition_index 99
python $PYTHONPATH/cli.py generate_additional_instances ton_2018_netupdate_instances_100_199  0 --min_number_nodes 15 --max_number_nodes 35 --min_number_wps 1 --max_number_wps 5 --min_repetition_index 100 --max_repetition_index 199 ton_2018_netupdate_instances_0_99.cpickle
python $PYTHONPATH/cli.py generate_additional_instances ton_2018_netupdate_instances_200_249  0 --min_number_nodes 15 --max_number_nodes 35 --min_number_wps 1 --max_number_wps 5 --min_repetition_index 200 --max_repetition_index 249 ton_2018_netupdate_instances_0_99.cpickle ton_2018_netupdate_instances_100_199.cpickle
```

Multiple of these instance storages can be merged by using the following CLI command:

```
python $PYTHONPATH/cli.py merge_instance_storages ton_2018_netupdate_instances.cpickle ton_2018_netupdate_instances ton_2018_netupdate_instances_0_99.cpickle ton_2018_netupdate_instances_100_199.cpickle ton_2018_netupdate_instances_200_249.cpickle
```

## Execution of Instances

To allow for the parallel execution of instances, we use the notion of slices. In particular, the command to execute a slice of an instance
storage may look like this:

```
python $PYTHONPATH/cli.py execute_experiments ton_2018_netupdate_instances_0_99.cpickle results_ton_2018_netupdate_instances_0_99 0 40 both both both --timelimit 1000 --threads 1 --mip_gap 0.0001 --numeric_focus 2 | tee -i results_ton_2018_netupdate_instances_0_99_sub_0.log
```

In the above command the slice to execute (**0**), the number of slices (**40**), the algorithm options (3 times **both**) as well as
Gurobi settings are passed to determine under which parameters the MIP formulations should be solved. 
Note that the trailing **tee** command just redirects the output of the process to a specific log-file.

To enable the execution of many instances in parallel, the command-line interface offers the following command to automatically create
**bash** files to start as many processes as wished for.

To execute the instances of an instance storage container using 40 processes, the following command can be used to construct the 
appropriate **bash**-file:

```
python $PYTHONPATH/cli.py write_bash_file_for_parallel_execution execution_ton_0_99_scriptmark.sh ton_2018_netupdate_instances_0_99.cpickle results_ton_2018_netupdate_instances_0_99 40 both both both --timelimit 1000 --threads 1 --mip_gap 0.0001 --numeric_focus 2
```

## Aggregation of Instances Solutions

After the results have been stored into various experiment solution storages, these results can be aggregated using the command-line
interface using the following commmand:

```
python $PYTHONPATH/cli.py merge_experiment_storages ton_2018_netupdate_solution_storage.cpickle --new_identifier ton_2018_netupdate_instances results_ton_*.cpickle
```

Note that the solution storages contain a whole bunch of information on the solution process (temporal data). Accordingly, a lot
of RAM is needed to aggregate the storages. For the 26,250 instances and the 8 different algorithms, roughly 32 GB of RAM 
were necessary to aggregated the results, resulting in a 5 GB large cpickle file.

## Extraction of Data to be Plotted  

As mostly only the  overall runtime or the overall solution quality is used for plotting purposes and the intermediate solution
process is not of interest, we provide the functionality to extract the data of interest. Again, this is possible via a call of the CLI:

```
python $PYTHONPATH/cli.py create_extracted_experiment_data_storage ton_2018_netupdate_solution_storage.cpickle ton_2018_netupdate_solution_storage_extracted_data.cpickle
```

The resulting cpickle file has a size of less than 30 MB. Compared to the previous size of more than 5 GB for storing all the data,
the improvement is huge and the plotting can be done much quicker and without nearly as much RAM.

# Data of our Latest IEEE/ACM Transactions of Networking Submission

Within the **data/ton_2018_submission** directory, the instances and their results - as generated and executed according to the above 
description - can be found together with the generated plots. The code for the plot generation is currently not contained within the
repository but we plan on releasing it.

# Contact

Feel free to contact me at **mrost@inet.tu-berlin.de**.

