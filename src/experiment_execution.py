# MIT License
#
# Copyright (c) 2016-2018 Matthias Rost
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__author__ = 'Matthias Rost (mrost@inet.tu-berlin.de)'

import cPickle
import multiprocessing

import gurobi_interface as gi
import datamodel as dm


def execute_algorithm_multiprocess(instance, model_configuration, gurobi_settings, result_queue):
    ''' Instantiates a ModelCreator instance and solves the provided network update instance returning the result via
        the result queue. This function is used by the multiprocessing library to cmopute solutions in parallel.

    :param instance: NetworkUpdateInstance class
    :param model_configuration: which of the MIP models shall be used
    :param gurobi_settings: settings for gurobi (timelimits etc.)
    :param result_queue: queue via which the solution is returned
    :return:
    '''
    print model_configuration
    mc = None
    if model_configuration.decision_variant:
        gurobi_settings.mip_gap = 1.0
        mc = gi.ModelCreator(instance=instance, model_configuration=model_configuration, gurobi_settings=gurobi_settings)
    else:
        mc = gi.ModelCreator(instance=instance, model_configuration=model_configuration, gurobi_settings=gurobi_settings)
    solution = mc.compute_solution()
    result_queue.put(solution)


class ExperimentExecutor(object):
    ''' Executes the instances -- better: a slice of them -- in own processes using multiprocessing.

        The main input is an instance storage class, the number of "slices" to be considered and the slice which shall
        be executed. The result is stored in an ExperimentStorage class, such that the different ExperimentStorage
        results can be later on merged together. This allows to massively parallelize the computation of solutions by
        starting multiple python processes with different slices.

        Multiprocessing is used inside this class to execute each and every single experiment. The reason for that is
        to decrease the potential of increased memory usage due to memory leakage / slow garbage collection by python.

    '''

    def __init__(self, instance_storage, slice_to_execute, number_of_slices, model_configurations_to_execute, gurobi_settings):

        self.instance_storage = instance_storage
        self.slice_to_execute = slice_to_execute
        self.number_of_slices = number_of_slices
        self.model_configurations_to_execute = model_configurations_to_execute
        self.gurobi_settings = gurobi_settings

        self.instances_to_execute = None

        self.experiment_storage = dm.ExperimentStorage(self.instance_storage.identifier,
                                                       self.instance_storage.raw_instance_generation_parameters)



    def _create_partition_of_instances(self):
        self.instances_to_execute = {}
        for slice_number in range(self.number_of_slices):
            self.instances_to_execute[slice_number] = []

        slice_number = 0

        for x in self.instance_storage.contained_instances:
            self.instances_to_execute[slice_number].append(x)
            slice_number = (slice_number+1)% self.number_of_slices



    def execute_all_instances(self):
        ''' Computes solutions for all instances contained in the selected slice.

        :return: nothing
        '''

        if self.instances_to_execute is None:
            self._create_partition_of_instances()

        instance_indices_to_execute = self.instances_to_execute[self.slice_to_execute]

        counter = 1
        for instance_index in instance_indices_to_execute:

            instance = self.instance_storage.instance_dictionary[instance_index]

            for model_configuration in self.model_configurations_to_execute:

                result_queue = multiprocessing.Queue()

                print "\n\nEXPERIMENT_MANAGER: Starting experiment of instance {} of {}..\ninstance index is\t\t{}\nconfiguration is\t\t {}\n\n".format(counter, len(instance_indices_to_execute), instance_index, model_configuration)

                process = multiprocessing.Process(target=execute_algorithm_multiprocess, args=(instance, model_configuration, self.gurobi_settings, result_queue))
                print "starting {} .. ".format(model_configuration)
                process.start()

                result = result_queue.get()
                print "received result {}".format(result)
                process.join()
                result_queue.close()

                self.experiment_storage.add_instance_solution(instance=instance,
                                                              instance_index=instance_index,
                                                              instance_generation_parameter=self.instance_storage.numeric_index_to_parameter[instance_index],
                                                              model_configuration_representation=model_configuration.get_simple_tuple_representation(),
                                                              solution=result)


            counter += 1

    def pickle_experiment_storage(self, filename_base):
        filename = filename_base + "_{}_{}.cpickle".format(self.slice_to_execute, self.number_of_slices)
        if self.slice_to_execute == 0 and self.number_of_slices == 1:
            filename = filename_base + ".cpickle"
        with open(filename, "w") as f:
            cPickle.dump(self.experiment_storage, f)
        print "Experiment storage was written to {}. ".format(filename)


    def print_meta_information(self):
        print "The storage contains {} many experiments with the following keys..\n{}\n\n\n".format(len(self.instance_storage.contained_scenario_parameters), self.instance_storage.contained_scenario_parameters)

        print "The keys are distributed over the {} servers in the following fashion\n{}\n\n\n".format(self.number_of_slices, self.instances_to_execute)

        print "The following model_configurations are to be executed:\n{}".format(self.model_configurations_to_execute)

