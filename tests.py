# MIT License
#
# Copyright (c) 2016-2018 Matthias Rost (mrost AT inet DOT tu-berlin DOT de)
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

import datamodel as dm
import experiment_execution as ee
import cli

import itertools
import pytest
import cPickle

from datamodel import GurobiSettings


@pytest.fixture
def generation_parameters():
    return dm.InstanceGenerationParameters(nodes=[7,15],
                                           number_wps=[0,1,2],
                                           index=[x for x in range(0,3)])

class TestNetworkInstanceStorage():

    def test_generation_function_of_cli(self, generation_parameters):
        output_filename, instance_storage = cli.f_generate_instances("test_test", 1337, generation_parameters)

        assert instance_storage is not None, "no instance storage returned"

        set_of_triples = set()

        for number_nodes in generation_parameters.nodes:
            for wps in generation_parameters.number_wps:
                for index in generation_parameters.index:
                    set_of_triples.add((number_nodes, wps, index))



        for instance_key, instance in instance_storage.instance_dictionary.iteritems():
            assert instance is not None, "instance contained in the storage is none"

            gen_parameter = instance_storage.numeric_index_to_parameter[instance_key]

            generation_triple = (gen_parameter.nodes,
                                 gen_parameter.number_wps,
                                 gen_parameter.index)

            assert generation_triple in set_of_triples, "there exists an instance generated according to a specification not contained in the parameter list"
            set_of_triples.remove(generation_triple)

        assert len(set_of_triples) == 0, "there were more instances generated than specified"



@pytest.fixture
def model_configurations_to_execute():
    result = []

    bool_list = [False, True]
    for v1, v2, v3 in itertools.product(bool_list, bool_list, bool_list):
        print v1, v2, v3
        model_configuration = dm.ModelConfiguration(decision_variant=v1,
                                                    strong_loop_freedom=v2,
                                                    use_flow_extension=v3)
        result.append(model_configuration)

    return result


@pytest.fixture
def instance_storage_small_from_pickle():
    instance_storage = None
    with open("test_data/small_test_instance_storage.cpickle", "r") as f:
        instance_storage = cPickle.load(f)
    return instance_storage

@pytest.fixture
def gurobi_settings():
    return dm.GurobiSettings(timelimit=120, threads=1, mip_gap=0.01, numeric_focus=2)


class TestGurobi():

    def test_execution_of_stored_sample_instances_and_sanity_check_solutions(self,
                                                                             model_configurations_to_execute,
                                                                             gurobi_settings,
                                                                             generation_parameters):

        _, instance_storage = cli.f_generate_instances("test_test", 1337, generation_parameters)

        experiment_executor = ee.ExperimentExecutor(instance_storage,
                                                    0,
                                                    1,
                                                    model_configurations_to_execute,
                                                    gurobi_settings)

        experiment_executor.execute_all_instances()

        experiment_storage = experiment_executor.experiment_storage

        model_configuration_representations = [x.get_simple_tuple_representation() for x in model_configurations_to_execute]

        for instance_index in instance_storage.contained_instances:

            assert instance_index in experiment_storage.instance_solutions

            solutions_of_instance = experiment_storage.instance_solutions[instance_index]

            assert solutions_of_instance is not None

            #check that all solutions agree on feasibility

            print solutions_of_instance.keys()
            print model_configurations_to_execute[0]

            first_sol = solutions_of_instance[model_configuration_representations[0]]
            found_sol = first_sol.is_feasible()

            for model_config in model_configuration_representations:
                assert solutions_of_instance[model_config].is_feasible() == found_sol, "One configuration found a solution while the other didn't"

            optimal_solutions = {}

            if found_sol:
                #check that optimal solutions have the same objective value or better than non-optimal solutions
                for config_one in model_configuration_representations:
                    for config_two in model_configuration_representations:
                        if config_one[0][1] or config_two[0][1]:
                            continue
                        if config_one[2][1] != config_two[2][1]:
                            continue

                        if solutions_of_instance[config_one].is_optimal():
                            assert solutions_of_instance[config_one].get_number_of_rounds() <= solutions_of_instance[config_two].get_number_of_rounds(), \
                                "Optimal number of rounds is larger than non-optimal number of rounds or optimal rounds do no not agree"

                            optimal_solutions[config_one[2][1]] = solutions_of_instance[config_one].get_number_of_rounds()

                if False in optimal_solutions and True in optimal_solutions:
                    assert optimal_solutions[False] <= optimal_solutions[True], \
                        "Strong-loop freedom needs less rounds than relaxed-loop freedom (in optimal solutions)"

            else:
                print "Also contained infeasible scnearios!"











