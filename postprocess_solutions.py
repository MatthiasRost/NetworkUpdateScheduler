__author__ = 'Matthias Rost (mrost@inet.tu-berlin.de)'

import cPickle
import os
import datamodel as dm
import numpy as np


def load_pickle(filename):
    with open(filename, "r") as f:
        return cPickle.load(f)

def create_extracted_experiment_data_storage(original_experiment_storage):

    extracted_experiment_storage = dm.ExtractedExperimentDataStorage(original_experiment_storage.instance_storage_id)

    for instance_index, instance_solutions in original_experiment_storage.instance_solutions.iteritems():
        gen_params = original_experiment_storage.instance_generation_parameter[instance_index]
        for model_configuration_representation in instance_solutions.keys():

            solution = instance_solutions[model_configuration_representation]
            extracted_experiment_storage.add_solution_data(instance_index=instance_index,
                                                           gen_params=gen_params,
                                                           model_configuration_representation=model_configuration_representation,
                                                           netupdate_solution=solution)

    return extracted_experiment_storage


def obtain_nodes_to_optimal_solutions_per_model_config(extracted_experiment_data_storage, model_configurations):
    eeds = extracted_experiment_data_storage
    result = {}

    for umc in model_configurations:
        result[umc] = {}
        for node in eeds.igp_nodes:
            result[umc][node] = np.zeros(len(eeds.igp_wps)*len(eeds.igp_index))
            counter = 0
            for wp in eeds.igp_wps:
                for index in eeds.igp_index:
                    extracted_solution_data = eeds.gen_params_to_model_to_extracted_data[(node,wp,index)][umc]
                    if extracted_solution_data.classification == dm.ExtractedSolutionData.CLASS_OPTIMAL:
                        result[umc][node][counter] = extracted_solution_data.solution
                    else:
                        result[umc][node][counter] = np.NaN
                    counter += 1

    return result




