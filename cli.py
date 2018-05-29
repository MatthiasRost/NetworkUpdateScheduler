import click
import sys, os
import cPickle
import time
import multiprocessing
import math

import datamodel as dm
import experiment_execution as ee
import postprocess_solutions as pps


sys.path.insert(0, os.path.abspath('../'))


@click.group()
def cli():
    pass


def _get_instance_generation_settings(min_number_nodes,
                                      max_number_nodes,
                                      number_nodes_step,
                                      min_number_wps,
                                      max_number_wps,
                                      number_wps_step,
                                      min_repetition_index,
                                      max_repetition_index):
    nodes_list = [x for x in range(min_number_nodes, max_number_nodes + 1, number_nodes_step)]
    wps_list = [x for x in range(min_number_wps, max_number_wps + 1, number_wps_step)]
    index_list = [x for x in range(min_repetition_index, max_repetition_index + 1)]

    if len(nodes_list) == 0:
        raise Exception(
            "Cannot create instances with min_number_nodes: {}, max_number_nodes: {}, number_nodes_step: {}".format(
                min_number_nodes,
                max_number_nodes,
                number_nodes_step))

    if len(wps_list) == 0:
        click.confirm('"Instances will be generated WITHOUT any waypoints present. Do you want to continue?',
                      abort=True)

    if len(index_list) == 0:
        raise Exception("Cannot create instances with number_of_repetitions: {}".format(number_of_repetitions))

    instances_generation_parameters = dm.InstanceGenerationParameters(nodes=nodes_list,
                                                                      number_wps=wps_list,
                                                                      index=index_list)
    return instances_generation_parameters


#default parameters are based on the sigmetrics publication (2016)
@cli.command()
@click.argument('instance_storage_name')
@click.argument('seed', type=click.INT)
@click.option('--min_number_nodes', type=click.INT, default=10)
@click.option('--max_number_nodes', type=click.INT, default=30)
@click.option('--number_nodes_step', type=click.INT, default=1)
@click.option('--min_number_wps', type=click.INT, default=1)
@click.option('--max_number_wps', type=click.INT, default=3)
@click.option('--number_wps_step', type=click.INT, default=1)
@click.option('--min_repetition_index', type=click.INT, default=0)
@click.option('--max_repetition_index', type=click.INT, default=100)
def generate_instances(instance_storage_name,
                       seed,
                       min_number_nodes,
                       max_number_nodes,
                       number_nodes_step,
                       min_number_wps,
                       max_number_wps,
                       number_wps_step,
                       min_repetition_index,
                       max_repetition_index):

    instances_generation_parameters = _get_instance_generation_settings(min_number_nodes,
                                                                       max_number_nodes,
                                                                       number_nodes_step,
                                                                       min_number_wps,
                                                                       max_number_wps,
                                                                       number_wps_step,
                                                                       min_repetition_index,
                                                                       max_repetition_index)

    output_filename, instance_storage = f_generate_instances(instance_storage_name,
                                                             seed,
                                                             raw_instance_generation_parameters=instances_generation_parameters)


    with open(output_filename, "w") as f:
        print "\nWriting the instance storage container with id {} into file {}".format(instance_storage.identifier, output_filename)
        cPickle.dump(instance_storage, f)
        print "\nFile {} was written".format(output_filename)


#default parameters are based on the sigmetrics publication (2016)
@cli.command()
@click.argument('instance_storage_name')
@click.argument('seed', type=click.INT)
@click.option('--min_number_nodes', type=click.INT, default=10)
@click.option('--max_number_nodes', type=click.INT, default=30)
@click.option('--number_nodes_step', type=click.INT, default=1)
@click.option('--min_number_wps', type=click.INT, default=1)
@click.option('--max_number_wps', type=click.INT, default=3)
@click.option('--number_wps_step', type=click.INT, default=1)
@click.option('--min_repetition_index', type=click.INT, default=0)
@click.option('--max_repetition_index', type=click.INT, default=100)
@click.argument('previous_instance_containers', nargs=-1, type=click.Path())
def generate_additional_instances(instance_storage_name,
                                  seed,
                                  min_number_nodes,
                                  max_number_nodes,
                                  number_nodes_step,
                                  min_number_wps,
                                  max_number_wps,
                                  number_wps_step,
                                  min_repetition_index,
                                  max_repetition_index,
                                  previous_instance_containers):
    instances_generation_parameters = _get_instance_generation_settings(min_number_nodes,
                                                                        max_number_nodes,
                                                                        number_nodes_step,
                                                                        min_number_wps,
                                                                        max_number_wps,
                                                                        number_wps_step,
                                                                        min_repetition_index,
                                                                        max_repetition_index)

    already_known_instance_representations = set()
    maximal_seen_instance_index = -10000000000
    for filename in previous_instance_containers:
        with open(filename, "r") as f:
            print "\nReading instance storage from {}".format(filename)
            instance_storage = cPickle.load(f)
            print "\t..done."

            print "Starting to read instances..."
            for instance_index, instance in instance_storage.contained_instances.iteritems():
                already_known_instance_representations.add(instance.get_sequence_representation())
                if instance_index > maximal_seen_instance_index:
                    maximal_seen_instance_index = instance_index
                print "\t\tread instance with id {} and added representation to storage container..".format(instance_index)


    output_filename, instance_storage = f_generate_instances(instance_storage_name,
                                                             seed,
                                                             raw_instance_generation_parameters=instances_generation_parameters,
                                                             index_offset=maximal_seen_instance_index+1,
                                                             already_generated_instance_representations=already_known_instance_representations)

    with open(output_filename, "w") as f:
        print "\nWriting the instance storage container with id {} into file {}".format(instance_storage.identifier,
                                                                                        output_filename)
        cPickle.dump(instance_storage, f)
        print "\nFile {} was written".format(output_filename)

def f_generate_instances(instance_storage_name,
                         seed,
                         raw_instance_generation_parameters,
                         index_offset=0,
                         already_generated_instance_representations=None):

    output_filename = instance_storage_name + ".cpickle"

    output_string = ""

    output_string += "Generation of instances of {} is done according to the following parameters\n".format(output_filename)
    output_string += "\t seed: {}\n".format(seed)
    output_string += "\t instance generation parameters are...\n".format()
    output_string += "\t\t nodes:      {}\n".format(raw_instance_generation_parameters.nodes)
    output_string += "\t\t number_wps: {}\n".format(raw_instance_generation_parameters.number_wps)
    output_string += "\t\t indices:    {}\n\n".format(raw_instance_generation_parameters.index)



    print output_string

    with open(instance_storage_name + ".txt", "w") as f:
        f.write(output_string)
    print output_string

    print "\nStarting generation of instances..."

    instance_storage_id = output_filename + "[{}]".format(time.strftime("%d/%m/%Y--%H:%S"))

    instance_storage = dm.InstanceStorage(identifier=instance_storage_id,
                                      instance_generation_parameters=raw_instance_generation_parameters,
                                      seed=seed)
    instance_storage.generate(index_offset=index_offset,
                              generated_instance_representations=already_generated_instance_representations)

    print "\n...generated {} many instances.".format(instance_storage.number_of_instances)

    return output_filename, instance_storage

CONSTANT_YES = "yes"
CONSTANT_NO = "no"
CONSTANT_BOTH = "both"

def from_yes_no_both_to_list(string_value):
    result = []
    if CONSTANT_YES == string_value or CONSTANT_BOTH == string_value:
        result.append(True)
    if CONSTANT_NO == string_value or CONSTANT_BOTH == string_value:
        result.append(False)
    return result

def check_input_range_execution_parameters(slice_to_execute, number_of_slices, timelimit, threads, mip_gap, numeric_focus):
    if slice_to_execute < 0 or slice_to_execute >= number_of_slices:
        raise Exception("The slice to be executed must be in the range [0,1,...,number_of_slices-1]")

    if timelimit < 1:
        raise Exception("Timelimit must be greater than 0.")
    if threads <= 0 or threads > multiprocessing.cpu_count():
        raise Exception("Thread parameter must lie in the interval [1,...,{}].".format(multiprocessing.cpu_count()))
    if mip_gap < 0 or mip_gap > 1:
        raise Exception("mip_gap parameter must be in the interval [0,1]")
    if numeric_focus < 0 or numeric_focus > 3:
        raise Exception("numeric_focus parameter must be in {0,1,2,3}")

@cli.command()
@click.argument('instance_storage_filename')
@click.argument('output_base_name')
@click.argument('slice_to_execute', type=click.INT)
@click.argument('number_of_slices', type=click.INT)
@click.argument('decision_variant', type=click.Choice([CONSTANT_YES, CONSTANT_NO, CONSTANT_BOTH]))
@click.argument('strong_loop_freedom', type=click.Choice([CONSTANT_YES, CONSTANT_NO, CONSTANT_BOTH]))
@click.argument('flow_extension', type=click.Choice([CONSTANT_YES, CONSTANT_NO, CONSTANT_BOTH]))
@click.option('--timelimit', type=click.INT, default=600)
@click.option('--threads', type=click.INT, default=1)
@click.option('--mip_gap', type=click.FLOAT, default=0.001)
@click.option('--numeric_focus', type=click.INT, default=0)
def execute_experiments(instance_storage_filename,
                        output_base_name,
                        slice_to_execute,
                        number_of_slices,
                        decision_variant,
                        strong_loop_freedom,
                        flow_extension,
                        timelimit=None,
                        threads=None,
                        mip_gap=None,
                        numeric_focus=None):

    check_input_range_execution_parameters(slice_to_execute, number_of_slices, timelimit, threads, mip_gap, numeric_focus)

    decision_choice_list = from_yes_no_both_to_list(decision_variant)
    strong_loop_freedom_list = from_yes_no_both_to_list(strong_loop_freedom)
    flow_extension_list = from_yes_no_both_to_list(flow_extension)

    f_execute_experiments(instance_storage_filename=instance_storage_filename,
                          output_base_name=output_base_name,
                          slice_to_execute=slice_to_execute,
                          number_of_slices=number_of_slices,
                          decision_variant_choices=decision_choice_list,
                          strong_loop_freedom_choices=strong_loop_freedom_list,
                          flow_extension_choices=flow_extension_list,
                          timelimit=timelimit,
                          threads=threads,
                          mip_gap=mip_gap,
                          numeric_focus=numeric_focus)



def f_execute_experiments(instance_storage_filename,
                          output_base_name,
                          slice_to_execute,
                          number_of_slices,
                          decision_variant_choices,
                          strong_loop_freedom_choices,
                          flow_extension_choices,
                          timelimit=None,
                          threads=None,
                          mip_gap=None,
                          numeric_focus=None):
    instance_storage = None
    with open(instance_storage_filename, "r") as f:
        print "\nReading instance storage from {}".format(instance_storage_filename)
        instance_storage = cPickle.load(f)
        print "\t..done."


    model_configurations = []
    for decision_value in decision_variant_choices:
        for slf_value in strong_loop_freedom_choices:
            for flow_extension_value in flow_extension_choices:
                model_configurations.append(dm.ModelConfiguration(decision_variant=decision_value,
                                                                  strong_loop_freedom=slf_value,
                                                                  use_flow_extension=flow_extension_value))



    gurobi_settings = dm.GurobiSettings(timelimit=timelimit,
                                        threads=threads,
                                        mip_gap=mip_gap,
                                        numeric_focus=numeric_focus)

    executor = ee.ExperimentExecutor(instance_storage,
                                     slice_to_execute,
                                     number_of_slices,
                                     model_configurations_to_execute=model_configurations,
                                     gurobi_settings=gurobi_settings)

    print "starting execution of instances.."
    executor.execute_all_instances()
    print "\t..done. All experiments are finished."
    executor.pickle_experiment_storage(output_base_name)



@cli.command()
@click.argument('filename_to_write')
@click.argument('instance_storage_filename')
@click.argument('output_base_name')
@click.argument('number_of_processes', type=click.INT)
@click.argument('decision_variant', type=click.Choice([CONSTANT_YES, CONSTANT_NO, CONSTANT_BOTH]))
@click.argument('strong_loop_freedom', type=click.Choice([CONSTANT_YES, CONSTANT_NO, CONSTANT_BOTH]))
@click.argument('flow_extension', type=click.Choice([CONSTANT_YES, CONSTANT_NO, CONSTANT_BOTH]))
@click.option('--timelimit', type=click.INT, default=600)
@click.option('--threads', type=click.INT, default=1)
@click.option('--mip_gap', type=click.FLOAT, default=0.01)
@click.option('--numeric_focus', type=click.INT, default=0)
def write_bash_file_for_parallel_execution(filename_to_write,
                                           instance_storage_filename,
                                           output_base_name,
                                           number_of_processes,
                                           decision_variant,
                                           strong_loop_freedom,
                                           flow_extension,
                                           timelimit=None,
                                           threads=None,
                                           mip_gap=None,
                                           numeric_focus=None):

    check_input_range_execution_parameters(0, 1, timelimit, threads, mip_gap, numeric_focus)

    output_file = "#!/bin/bash\n\n"
    for i in range(number_of_processes):
        output_file += "(python cli.py execute_experiments {} {} {} {} {} {} {} " \
                       "--timelimit {} --threads {} --mip_gap {} --numeric_focus {} | tee -i {}_sub_{}.log) &\n".format(instance_storage_filename,
                                                                                                                        output_base_name,
                                                                                                                        i,
                                                                                                                        number_of_processes,
                                                                                                                        decision_variant,
                                                                                                                        strong_loop_freedom,
                                                                                                                        flow_extension,
                                                                                                                        timelimit,
                                                                                                                        threads,
                                                                                                                        mip_gap,
                                                                                                                        numeric_focus,
                                                                                                                        output_base_name,
                                                                                                                        i)

    with open(filename_to_write, 'w') as f:
        f.write(output_file)



@cli.command()
@click.argument("output_filename", type=click.Path())
@click.argument('files', nargs=-1, type=click.Path())
def merge_experiment_storages(output_filename, files):
    resulting_experiment_storage = dm.ExperimentStorage(instance_storage_id="", raw_instance_generation_parameters=None)

    for filename in files:
        other_experiment_storage = None
        with open(filename, "r") as f:
            print "Reading experiment storage from {}".format(filename)
            other_experiment_storage = cPickle.load(f)
        resulting_experiment_storage.import_results_from_other_experiment_storage(other_experiment_storage)


    with open(output_filename, "wb") as f:
        cPickle.dump(resulting_experiment_storage, f)

    print "Written merged storage to {}".format(output_filename)



@cli.command()
@click.argument("experiment_storage_pickle", type=click.Path())
def print_results_of_experiment_storage(experiment_storage_pickle):

    experiment_storage = None
    with open(experiment_storage_pickle, "r") as f:
        experiment_storage = cPickle.load(f)

    output = ""
    for instance_index in sorted(experiment_storage.contained_instances.keys()):
        output += "index: {}\n".format(instance_index)
        for model_configuration_rep in experiment_storage.instance_solutions[instance_index]:
            solution = experiment_storage.instance_solutions[instance_index][model_configuration_rep]
            output += "\t\t config: {}\t --> " \
                      "number_rounds: {};\t " \
                      "optimal: {};\t " \
                      "wall clock: {};\t " \
                      "gurobi: {} \n".format(model_configuration_rep,
                                             solution.get_number_of_rounds(),
                                             solution.is_optimal(),
                                             solution.status.runtime_wall_clock,
                                             solution.status.runtime_gurobi)
        output += "\n"

    print output



@cli.command()
@click.argument("output_filename", type=click.Path())
@click.argument('files', nargs=-1, type=click.Path())
def create_instance_storage_for_hard_instances(output_filename,
                                               files):
    instance_storage = dm.InstanceStorage(identifier="hard_instances_8_8192",
                                          instance_generation_parameters="from_file",
                                          seed=-1)

    for i, file in enumerate(files):
        print "reading instance from file {}".format(file)
        instance = dm.NetworkUpdateInstance()
        instance.read_from_edge_only_file(file)

        upper_bound_on_rounds = int(math.ceil(6.0*math.log(instance.number_of_nodes,2)) + 2)

        instance.rounds = min(upper_bound_on_rounds, instance.rounds)

        instance_storage.contained_instances.append(i)
        instance_storage.instance_dictionary[i] = instance
        instance_storage.numeric_index_to_parameter[i] = "from_file"

        instance.write_to_file(file + "new")


    instance_storage.number_of_instances = len(instance_storage.contained_instances)

    print instance_storage

    print "writing to {}..".format(output_filename)
    with open(output_filename, "w") as f:
        cPickle.dump(instance_storage, f)
    print "\t..finished writing the file"


@cli.command()
@click.argument("original_experiment_storage_filename", type=click.Path())
@click.argument("extracted_experiment_data_storage_filename", type=click.Path())
def create_extracted_experiment_data_storage(original_experiment_storage_filename,
                                             extracted_experiment_data_storage_filename):

    original_experiment_storage = None
    with open(original_experiment_storage_filename, "r") as f:
        original_experiment_storage = cPickle.load(f)

    extracted_experiment_storage = pps.create_extracted_experiment_data_storage(original_experiment_storage)
    extracted_experiment_storage.collect_instance_generation_parameters()
    if extracted_experiment_storage.check_completeness_of_data():
        print "data is complete!"
    else:
        raise Exception("Data is missing!")


    with open(extracted_experiment_data_storage_filename, "w") as f:
        cPickle.dump(extracted_experiment_storage, f)
    print "written extracted experiment data storage to {}".format(extracted_experiment_data_storage_filename)


#default parameters are based on the sigmetrics publication (2016)
@cli.command()
@click.argument('seed', type=click.INT)
@click.option('--number_nodes', type=click.INT, default=10)
@click.option('--number_wps', type=click.INT, default=1)
@click.option('--max_iterations', type=click.INT, default=1000)
def inspect_uniqueness_of_instances(seed,
                                    number_nodes,
                                    number_wps,
                                    max_iterations):
    import time
    start = time.time()


    unique_tuples = set()
    last_minutes = -1
    for i in range(max_iterations):
        instance = dm.NetworkUpdateInstance()
        try:
            instance.generate_randomly(number_nodes, number_wps)
        except Exception as e:
            print "\t\t\t\t\tfailed generation: {}".format(e)
            continue

        instance_representation = instance.get_sequence_representation()

        current_time = time.time()

        other_minutes, _ = divmod(current_time - start, 60)

        hours, rem = divmod(current_time - start, 3600)
        minutes, seconds = divmod(rem, 60)

        if other_minutes != last_minutes:
            last_minutes = other_minutes
            print("{:0>2}:{:0>2}:{:0>2}: -- still working --".format(int(hours), int(minutes), int(seconds), len(unique_tuples)))

        if instance_representation not in unique_tuples:

            unique_tuples.add(instance_representation)

            print("{:0>2}:{:0>2}:{:0>2}: {} many unique instances".format(int(hours), int(minutes), int(seconds), len(unique_tuples)))






    print unique_tuples

    print "\n\n\n{} unique instances among the {} generated.".format(len(unique_tuples),
                                                                     number_of_repetitions)


if __name__ == '__main__':
    cli()

