
# Overview

This repository contains algorithms and a simulation framework to schedule **loop-free network** updates that can also
take **waypoints**  into account.

The code is written in **Python2.7** and requires some few packages, most notably **Gurobi**, a commercial Mixed-Integer Programming solver, which is free for academic use. 

The code has been the basis for computational evaluations within the following publications:

**[1]** Arne Ludwig, Szymon Dudycz, Matthias Rost, and Stefan Schmid: **"Transiently Policy-Compliant Network Updates"**. IEEE/ACM Transactions on Networking (TON) (to appear).

**[2]** Klaus-Tycho Foerster, Arne Ludwig, Jan Marcinkowski, and Stefan Schmid: **"Loop-Free Route Updates for Software-Defined Networks"**. IEEE/ACM Transactions on Networking (TON), 2018.

**[3]** Arne Ludwig, Szymon Dudycz, Matthias Rost, and Stefan Schmid: **"Transiently Secure Network Updates"**. 42nd ACM SIGMETRICS, Antibes Juan-les-Pins, France, June 2016.

**[4]** Arne Ludwig, Matthias Rost, Damien Foucard, and Stefan Schmid: **"Good Network Updates for Bad Packets: Waypoint Enforcement Beyond Destination-Based Routing Policies"**. 13th ACM Workshop on Hot Topics in Networks (HotNets), Los Angeles, California, USA, October 2014.

# Structure

* The folder **[network_update](network_update/)** contains the sources (information on how to install and use the sources are given below).
* The folder **[test](test/)** contains some simple tests which can be executed using **pytest** after installing the package.
* The folder **[minimal_example](minimal_example/)** contains a bash-file to generate, execute, and plot the results of a small example evaluation.
* The folder **[paper_data_and_plots](paper_data_and_plots/)** contains the raw data (instances, extracted data) together with the resulting plots of our most recent papers [1,2]. 
  In particular, the folder **[Transiently_Policy_Compliant_Network_Updates](paper_data_and_plots/Transiently_Policy_Compliant_Network_Updates/)** contains the data pertaining to the paper [1] (and extending the evaluations presented in [3,4]), while the the folder **[Loop_Free_Route_Updates_for_SDNs](paper_data_and_plots/Loop_Free_Route_Updates_for_SDNs/)** contains the data pertaining to the paper [2].


# Dependencies and Requirements

The network_update library requires Python 2.7. Required python libraries: gurobipy, numpy, cPickle, matplotlib. 

Gurobi must be installed and the .../linux64/lib directory added to the environment variable LD_LIBRARY_PATH.

**Note**: Our source was only tested on Linux (specifically Ubuntu 14 and Ubuntu 16).  

# Installation

To install the code, i.e. the **network_update** package, we provide a setup script. Simply execute from within network_update's root directory: 

```
pip install .
```

Furthermore, if the code base will be edited by you, we propose to install it as editable:
```
pip install -e .
```
When choosing this option, sources are not copied during the installation but the local sources are used: changes to
the sources are directly reflected in the installed package.

We generally propose to install **network_update** into a virtual environment.


# Code Struture

The code is structured as follows:

 * **datamodel.py** contains all structures to store (and generate) network update instances and their solution.
 * **experiment_execution.py** contains the code to execute slices of instances.
 * **gurobi_interface.py** contains the different MIP formulations for solving the network update instances (specifically, see papers [1,3]).
 * **postprocess_solutions.py** allows to extract the most important data from the solution.
 * **cli.py** provides the command-line interface to generate, execute and evaluate the experiments (see below).
 * **visualization.py** provides the functionality to plot several sorts of graphs, specifically the ones used in the most recent papers [1,2].
 
 # Example: Generation, Execution, Plotting of Data for Paper [1]
 
In the following we shortly outline how the command-line interface can be used to generate and execute some instances. 
Our examples are based on our most recent paper [1] to appear in **IEEE/ACM journal Transactions on Networking** and the following code is also encapsulated in the **[generation_execution_plotting.sh](paper_data_and_plots/Transiently_Policy_Compliant_Network_Updates/generation_execution_plotting.sh)** contained in the folder **[Transiently_Policy_Compliant_Network_Updates](paper_data_and_plots/Transiently_Policy_Compliant_Network_Updates/)**. 
 

## Generation of Instances


The following commands were used to create 3 different instance storages containing 100, 100 and 50 instances for node numbers
ranging from 15 to 35 and waypoints ranging from 1 to 5. To only generate unique instances (and not draw the same instance) multiple times,
the previously generated instance containers should be passed to the **generate_additonal_instances** function.

```
python -m network_update.cli generate_instances instances_ton_N_15-35_W_1-5_I_0-99  0 --min_number_nodes 15 --max_number_nodes 35 --min_number_wps 1 --max_number_wps 5 --min_repetition_index 0 --max_repetition_index 99

python -m network_update.cli generate_additional_instances instances_ton_N_15-35_W_1-5_I_100-199  0 --min_number_nodes 15 --max_number_nodes 35 --min_number_wps 1 --max_number_wps 5 --min_repetition_index 100 --max_repetition_index 199 instances_ton_N_15-35_W_1-5_I_0-99.cpickle

python -m network_update.cli generate_additional_instances instances_ton_N_15-35_W_1-5_I_200-249  0 --min_number_nodes 15 --max_number_nodes 35 --min_number_wps 1 --max_number_wps 5 --min_repetition_index 200 --max_repetition_index 249 instances_ton_N_15-35_W_1-5_I_0-99.cpickle instances_ton_N_15-35_W_1-5_I_100-199.cpickle
```

Multiple of these instance storages can be merged by using the following CLI command:

```
python -m network_update.cli merge_instance_storages instances_ton_N_15-35_W_1-5_I_0-249.cpickle  instances_ton_N_15-35_W_1-5_I_0-99.cpickle instances_ton_N_15-35_W_1-5_I_100-199.cpickle instances_ton_N_15-35_W_1-5_I_200-249.cpickle
```

## Execution of Instances

To allow for the parallel execution of instances, we use the notion of slices. In particular, the command to execute a slice of an instance
storage may look like this:

```
python -m network_update.cli execute_experiments instances_ton_N_15-35_W_1-5_I_0-99.cpickle results_instances_ton_N_15-35_W_1-5_I_0-99 0 40 both both both --timelimit 1000 --threads 1 --mip_gap 0.0001 --numeric_focus 2 | tee -i results_ton_2018_netupdate_instances_0_99_sub_0.log
```

In the above command the slice to execute (**0**), the number of slices (**40**), the algorithm options (3 times **both**) as well as
Gurobi settings are passed to determine under which parameters the MIP formulations should be solved. 
Note that the trailing **tee** command just redirects the output of the process to a specific log-file.

To enable the execution of many instances in parallel, the command-line interface offers the following command to automatically create
**bash** files to start as many processes as wished for.

To execute the instances of an instance storage container using 40 processes, the following command can be used to construct the 
appropriate **bash**-file:

```
python -m network_update.cli write_bash_file_for_parallel_execution execution_ton_0-99_script.sh instances_ton_N_15-35_W_1-5_I_0-99.cpickle solutions_instances_ton_N_15-35_W_1-5_I_0-99 40 both both both --timelimit 1000 --threads 1 --mip_gap 0.0001 --numeric_focus 2
```

## Aggregation of Instances Solutions

After the results have been stored into various experiment solution storages, these results can be aggregated using the command-line
interface using the following commmand:

```
python -m network_update.cli merge_experiment_storages solutions_ton_N_15-35_W_1-5_I_0-249.cpickle --new_identifier solutions_ton_N_15-35_W_1-5_I_0-249 solutions_instances_ton_*.cpickle
```

Note that the solution storages contain a whole bunch of information on the solution process (temporal data). Accordingly, a lot
of RAM is needed to aggregate the storages. For the 26,250 instances and the 8 different algorithms of [1], roughly 32 GB of RAM 
were necessary to aggregate the results, resulting in a 5 GB large cpickle file.

## Extraction of Data to be Plotted  

As mostly only the  overall runtime or the overall solution quality is used for plotting purposes and the intermediate solution
process is not of interest, we provide the functionality to extract the data of interest. Again, this is possible via a call of the CLI:

```
python -m network_update.cli create_extracted_experiment_data_storage solutions_ton_N_15-35_W_1-5_I_0-249.cpickle solutions_ton_N_15-35_W_1-5_I_0-249_extracted_data.cpickle
```

The resulting cpickle file has a size of less than 30 MB. Compared to the previous size of more than 5 GB for storing all the data,
the improvement is huge and the plotting can be done much quicker and without nearly as much RAM.

## Plotting Data
Finally, the plots can be created using the following command.

```
python -m network_update.cli make_plots_ton_tpc solutions_ton_N_15-35_W_1-5_I_0-249_extracted_data.cpickle ./plots/
```
Here, all relevant plots pertaining to the papers [1,3,4] are plotted and stored in the **./plots/** folder (see **[here](paper_data_and_plots/Transiently_Policy_Compliant_Network_Updates/plots/)**). 

In a similar fashion, the plots for the paper [2] can be plotted, by using the following command:
```
python -m network_update.cli make_plots_ton_lfru solutions_ton_N_15-35_W_1-5_I_0-249_extracted_data.cpickle
```
# Contact

Feel free to contact me at **mrost@inet.tu-berlin.de** for any questions regarding the source code.

