__author__ = 'Matthias Rost (mrost@inet.tu-berlin.de)'

import copy
import random
import time
import math
import sys
import itertools
from collections import namedtuple


import gurobipy
from gurobipy import GRB

class NetworkUpdateInstance(object):

    '''Encapsulates a network update instance.

    Represents an instance of the network update instance by representing the common set of nodes, the old policy
    (old_edges) the new policy (new_edges) together with the common start and end node and a dictionary of waypoints.

    '''

    def __init__(self):
        self.nodes = []
        self.old_edges = []
        self.new_edges = []
        self.rounds = None
        self.start = None
        self.end = None
        self.wp = {}
        self.fixings = {}

        self.number_of_nodes = None
        self.number_of_waypoints = None


    def read_from_file(self, filename):
        '''Loads a scenario from file

        :param filename:
        :return: nothing, the contents of the file are placed in the NetworkUpdateInstance-instance
        '''
        content = []
        with open(filename) as f:
            content = f.readlines()

        print "reading input...\n"

        for line in content:
            splitted = line.split()
            if splitted != []:
                if len(splitted) == 3:
                    print splitted[0], " ", splitted[1], " ", splitted[2], " ",
                elif len(splitted) == 2:
                    print splitted[0], " ", splitted[1], " "
                else:
                    print "canont parse line '{}'; discarding it".format(line)
                if splitted[0] == "V":
                    self.nodes.append(int(splitted[1]))
                if splitted[0] == "O":
                    self.old_edges.append((int(splitted[1]),int(splitted[2])))
                if splitted[0] == "N":
                    self.new_edges.append((int(splitted[1]),int(splitted[2])))
                if splitted[0] == "S":
                    self.start = int(splitted[1])
                if splitted[0] == "E":
                    self.end = int(splitted[1])
                if splitted[0] == "W":
                    self.wp[int(splitted[1])] = int(splitted[2])
                if splitted[0] == "R":
                    self.rounds = int(splitted[1])
                if splitted[0] == "F":
                    if "[" in splitted[2] and "]" in splitted[2]:
                        tmp = splitted[2][1:len(splitted[2])-1]
                        print "was {} is {}".format(splitted[2], tmp)
                        list = []
                        if tmp != "":
                            list = [int(value) for value in tmp.split(",")]
                        self.fixings[int(splitted[1])] = list
                    else:
                        self.fixings[int(splitted[1])] = int(splitted[2])

        self.number_of_nodes = len(self.nodes)
        self.number_of_waypoints = len(self.wp.keys())


    def read_from_edge_only_file(self, filename):
        content = []
        print "reading input...\n"
        with open(filename, "r") as f:
            content = f.readlines()

        reading_old = True
        previous = None
        for line in content:
            if "new rules" in line:
                reading_old = False
                print self.old_edges
                previous = None
                self.start = self.old_edges[0][0]
                self.end = self.old_edges[-1][1]

            if "rules" in line:
                continue

            splitted = line.split()
            print splitted
            if len(splitted) < 1:
                continue
            node = int(splitted[0])

            if previous is None:
                previous = node
                continue

            if reading_old:
                self.old_edges.append((previous,node))
                previous = node
            else:
                self.new_edges.append((previous, node))
                previous = node


        self.number_of_waypoints = 0
        self.nodes = [x for x in range(self.start, self.end+1)]
        self.number_of_nodes = self.end
        self.rounds = self.number_of_nodes-1



    def write_to_file(self, filename):
        ''' Writes the instance to a file.

        :param filename:
        :return: nothing
        '''
        with open(filename, "w") as f:
            for node in self.nodes:
                f.write("V {}\n".format(node))
            for (s,t) in self.old_edges:
                f.write("O {} {}\n".format(s,t))
            for (s,t) in self.new_edges:
                f.write("N {} {}\n".format(s,t))
            f.write("S {}\n".format(self.start))
            f.write("E {}\n".format(self.end))
            f.write("R {}\n".format(self.rounds))
            for i, wp in self.wp.iteritems():
                f.write("W {} {}\n".format(i, wp))
            for r in sorted(self.fixings.keys()):
                if len(self.fixings[r]) > 0:
                    lala = ",".join([str(x) for x in self.fixings[r]])
                    print lala
                    f.write("F {} [{}]\n".format(r, lala))
                else:
                    f.write("F {} []\n".format(r))


    def generate_randomly(self, number_of_nodes, number_of_waypoints, random_instance=None, debug=False, max_iterations=10000):
        '''Generates a network update instance (uniformly) at random.

        :param number_of_nodes: number of nodes that the instance will have
        :param number_of_waypoints: number of waypoints that will be generated
        :param random_instance: instance of random.Random to be used; if None, the default instance is used.
        :return:
        '''

        if random_instance is None:
            random_instance = random.Random()

        self.nodes = [(x+1) for x in range(number_of_nodes)]
        self.old_edges = [(x+1,x+2) for x in range(number_of_nodes-1)]

        nodes_copy = copy.deepcopy(self.nodes[1:number_of_nodes-1])

        good = False
        wp_copies = None
        counter = 0
        new_node_order = None
        while not good and counter < max_iterations:

            good = True
            random_instance.shuffle(nodes_copy)
            #Arne taught me well
            wp_copies = copy.deepcopy(nodes_copy[0:number_of_waypoints])
            wp_copies.sort()

            #at this point, the waypoints should be spread out "reasonably"

            for i in range(number_of_waypoints):
                self.wp[i] = wp_copies[i]

            new_node_order = copy.deepcopy(self.nodes[1:number_of_nodes-1])

            random_instance.shuffle(new_node_order)

            #check whether we don't have any overlaps in edges from
            for index in range(number_of_nodes-2):
                if index == 0:
                    if new_node_order[index] == 2:
                        #would induce the edge (1,2), which is not allowed
                        good = False
                if index < number_of_nodes - 3:
                    if new_node_order[index] + 1 == new_node_order[index+1]:
                        good = False
                elif index == number_of_nodes-3:
                    if new_node_order[index] == number_of_nodes -1:
                        good = False

            #check whether the order of the waypoints is correct
            if len(self.wp.keys()) > 0:
                last_waypoint_position = new_node_order.index(self.wp[0])
                for i in range(1,number_of_waypoints):
                    current_wp = new_node_order.index(self.wp[i])

                    if current_wp < last_waypoint_position:
                        good = False

                    last_waypoint_position = current_wp

            counter += 1
            if counter % 100000 == 0:
                if debug: print "no solution after {} many iterations".format(counter)

        if not good:
            raise ValueError("Instance Generation failed.")
        if debug: print "instance generation took {} many tries".format(counter)

        self.new_edges.append((1,new_node_order[0]))
        for i in range(len(new_node_order)-1):
            self.new_edges.append((new_node_order[i], new_node_order[i+1]))
        self.new_edges.append((new_node_order[len(new_node_order)-1], number_of_nodes))

        #some final thoughts
        self.rounds = number_of_nodes-1
        self.start = 1
        self.end = number_of_nodes

        self.number_of_nodes = number_of_nodes
        self.number_of_waypoints = number_of_waypoints

    def get_sequence_representation(self):
        list_representation = []
        list_representation.append("nodes:")
        list_representation.extend(self.nodes)
        list_representation.append("old_edges:")
        list_representation.extend(self.old_edges)
        list_representation.append("new_edges:")
        list_representation.extend(self.new_edges)
        list_representation.append("way_points:")
        for i in range(self.number_of_waypoints):
            list_representation.append(self.wp[i])

        return tuple(list_representation)


class NetworkUpdateInstanceSolution(object):

    '''Encapsulates the solution of a network update instance together with meta-data.

    In particular, the meta-data is two-fold:
    - firstly, a status (GurobiStatus) is used to indicate the final Gurobi state.
    - secondly, a temporal log can be handed over which represents the most important aspects of the temporal solution
      process.

    '''

    def __init__(self, status, temporal_log,  solution_schedule=None):
        self.status = status
        self.temporal_log = temporal_log
        self.solution_schedule = solution_schedule


    def is_feasible(self):
        return self.status.is_feasible()

    def is_optimal(self):
        return self.status.is_optimal()

    def get_number_of_rounds(self):
        if self.status.obj_value is not None and self.status.obj_value < GRB.INFINITY:
            return int(round(self.status.obj_value))
        return -1

    def __str__(self):
        result = ""
        result += "Status code {}\n".format(self.status)
        result += "\n\nlog entries:\n"
        for entry in self.temporal_log.log_entries:
            result += "entry: {}\n".format(entry)
        result += "\n"
        result += "Schedule: {}\n\n".format(self.solution_schedule)
        return result



class ModelConfiguration(object):

    '''Specifies the specific Mixed-Integer Program model considered.

    Options are: decision variant (no optimization of rounds), whether strong loop freedom is used or not, and whether
    the flow extension shall be used.

    '''

    def __init__(self,
                 decision_variant,
                 strong_loop_freedom,
                 use_flow_extension):

        self.decision_variant = decision_variant
        self.strong_loop_freedom = strong_loop_freedom
        self.use_flow_extension = use_flow_extension

        self._str = "{}{}{}".format(self.decision_variant,
                                    self.strong_loop_freedom,
                                    self.use_flow_extension)
        self._hash = self._str.__hash__()


    def __ne__(self, other):
        result = (other == self)
        if result == NotImplemented:
            return NotImplemented
        return not result

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if self.decision_variant == other.decision_variant and \
                            self.strong_loop_freedom == other.strong_loop_freedom and \
                            self.use_flow_extension == other.use_flow_extension:
                return True
            else:
                return False
        else:
            return NotImplemented

    def get_simple_tuple_representation(self):
        return (("Decision", self.decision_variant), ("FlowExtension", self.use_flow_extension), ("StrongLoopFreedom", self.strong_loop_freedom))

    def __hash__(self):
        return self._hash

    def __str__(self):
        return "Decision variant: {};\t\tSLF: {};\t\tflow extension: {}".format(self.decision_variant,
                                                                                self.strong_loop_freedom,
                                                                                self.use_flow_extension)


class InstanceGenerationParameters(object):

    '''Simple class to store the generation parameters of instances.

    Note that the values stored in the class might be lists (if used in the generation process).

    '''

    def __init__(self, nodes, number_wps, index):
        self.nodes = nodes
        self.number_wps = number_wps
        self.index = index


    def __str__(self):
        return "InstanceGenerationParameters[nodes:{}, number_wps: {}, indices: {}]".format(self.nodes, self.number_wps, self.index)

    def __eq__(self, other):
        if not isinstance(other, InstanceGenerationParameters):
            # Don't recognise "other", so let *it* decide if we're equal
            return NotImplemented
        if self.nodes != other.nodes:
            print "nodes do not match"
            return False
        if self.number_wps != other.number_wps:
            print "number wps do not match"
            return False
        if self.index != other.index:
            print "indices do not match"
            return False
        return True

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result


class InstanceStorage(object):

    '''Class storing instances generated uniformly at random.

    Each instance storage has an identifier (which should be unique) to later trace the origin of experiments and
    allow for merging experimental results pertaining to the same identifier.
    Additionally, a seed must be passed which is used throughout the generation of the instances.

    The instances are stored by a numeric index: [0, ..., number_of_instances-1]

    '''

    def __init__(self, identifier, instance_generation_parameters, seed):
        '''

        :param identifier: should be an unique id to identify the instances contained in the storage.
        :param instance_generation_parameters:  an instance of the InstanceGenerationParameters containing LISTS instead
                                                of single values as this parameter describes a parameter space
        :param seed: integer seed for the generation process
        :return:
        '''

        self.identifier = identifier
        self.seed = seed
        self.raw_instance_generation_parameters = instance_generation_parameters
        self.contained_instances = []
        self.instance_dictionary = {}

        self.numeric_index_to_parameter = {}
        self.number_of_instances = 0

        self.random_instance = random.Random()
        self.random_instance.seed(self.seed)

    def _generate_unique_instance_according_to_parameters(self, index, instance_generation_parameters, generated_instance_representations, maximum_iterations):
        novel_instance = False
        instance = None
        instance_representation = None
        counter = 0
        while not novel_instance and counter < maximum_iterations:
            instance = NetworkUpdateInstance()
            instance.generate_randomly(instance_generation_parameters.nodes,
                                       instance_generation_parameters.number_wps,
                                       random_instance=self.random_instance)
            instance_representation = instance.get_sequence_representation()
            if instance_representation not in generated_instance_representations:
                novel_instance = True
            counter += 1
        if novel_instance:
            generated_instance_representations.add(instance_representation)
        if not novel_instance:
            raise ValueError("Could not generate novel instance!")

        self.instance_dictionary[index] = instance
        self.contained_instances.append(index)
        self.numeric_index_to_parameter[index] = instance_generation_parameters

    def generate(self, index_offset=0, maximum_iterations=10000):

        index = index_offset

        generated_instance_representations = set()

        if len(self.raw_instance_generation_parameters.number_wps) == 0:
            # generate without waypoints
            for params in itertools.product(self.raw_instance_generation_parameters.index,
                                            self.raw_instance_generation_parameters.nodes):

                instance_generation_parameters = InstanceGenerationParameters(nodes=params[1],
                                                                              number_wps=0,
                                                                              index=params[0])

                self._generate_unique_instance_according_to_parameters(index, instance_generation_parameters, generated_instance_representations, maximum_iterations)

                index += 1
        else:
            for params in itertools.product(self.raw_instance_generation_parameters.number_wps,
                                            self.raw_instance_generation_parameters.index,
                                            self.raw_instance_generation_parameters.nodes):

                instance_generation_parameters = InstanceGenerationParameters(nodes=params[2],
                                                                              number_wps=params[0],
                                                                              index=params[1])

                self._generate_unique_instance_according_to_parameters(index, instance_generation_parameters, generated_instance_representations, maximum_iterations)

                index += 1

        self.number_of_instances = index


class ExperimentStorage(object):

    '''Class storing the algorithmic results of potentially different model configurations for a common set of instances.

    The main functionality is described extensively in add_instance_solution.

    '''

    def __init__(self, instance_storage_id, raw_instance_generation_parameters):
        '''It's important that the instance_storage_id really corresponds to the InstanceStorage object.

        :param instance_storage_id:
        :return:
        '''
        self.instance_storage_id = instance_storage_id

        self.contained_instances = {}
        self.contained_model_configurations = set()

        self.instance_generation_parameter = {}
        self.instance_solutions = {}

        self.raw_instance_generation_parameters = raw_instance_generation_parameters

    def add_instance_solution(self,
                              instance,
                              instance_index,
                              instance_generation_parameter,
                              model_configuration_representation,
                              solution):

        '''Stores

        :param instance: NetworkUpdateInstance instance
        :param instance_index: index of this particular instance in the original InstanceStorage
        :param instance_generation_parameter: generation parameters of the particular instance
        :param model_configuration_representation: configuration of the model used to obtain the solution
        :param solution: a NetworkUpdateInstanceSolution class storing the results of Gurobi
        :return: nothing
        '''


        self.contained_instances[instance_index] = instance
        self.contained_model_configurations.add(model_configuration_representation)

        if instance_index in self.instance_generation_parameter:
            if self.instance_generation_parameter[instance_index] != instance_generation_parameter:
                raise Exception("Instance generation parameter do not match.")
        else:
            self.instance_generation_parameter[instance_index] = instance_generation_parameter

        if instance_index not in self.instance_solutions:
            self.instance_solutions[instance_index] = {}

        self.instance_solutions[instance_index][model_configuration_representation] = solution

    def import_results_from_other_experiment_storage(self, other_experiment_storage):
        print "starting merge with other experiment storage.."

        if self.raw_instance_generation_parameters is None and other_experiment_storage.raw_instance_generation_parameters is not None:
            print "overriding raw instance generation parameters"
            self.raw_instance_generation_parameters = other_experiment_storage.raw_instance_generation_parameters
        else:
            if self.raw_instance_generation_parameters != other_experiment_storage.raw_instance_generation_parameters:
                print "Raw instance generation parameters do not match!"
                print self.raw_instance_generation_parameters
                print other_experiment_storage.raw_instance_generation_parameters

        if self.instance_storage_id != "" and self.instance_storage_id != other_experiment_storage.instance_storage_id:
            raise Exception("Cannot merge experiment results referring to different instance storages.")
        if self.instance_storage_id == "":
            self.instance_storage_id = other_experiment_storage.instance_storage_id

        for key, value in other_experiment_storage.contained_instances.iteritems():
            if key in self.contained_instances:
                print "WARNING: experiment storage already contained instance"
            self.contained_instances[key] = value

        self.contained_model_configurations = self.contained_model_configurations.union(other_experiment_storage.contained_model_configurations)

        for key, value in other_experiment_storage.instance_generation_parameter.iteritems():
            self.instance_generation_parameter[key] = value

        for key, value in other_experiment_storage.instance_solutions.iteritems():
            if key not in self.instance_solutions:
                    self.instance_solutions[key] = {}
            for key2, value2 in value.iteritems():
                self.instance_solutions[key][key2] = value2

        print "\t... finished merge with other experiment storage."


class GurobiSettings(object):

    def __init__(self, timelimit=None, threads=None, mip_gap=None):
        self.timelimit = timelimit
        self.threads = threads
        self.mip_gap = mip_gap

        if self.timelimit is None:
            self.timelimit = 600
        if self.threads is None:
            self.threads = 1
        if self.mip_gap is None:
            self.mip_gap = 0.01

def is_infeasible_status(status):
    result = False
    if status == GurobiStatus.INFEASIBLE:
        result = True
    elif status == GurobiStatus.INF_OR_UNBD:
        result = True
    elif status == GurobiStatus.UNBOUNDED:
        result = True
    return result

def is_feasible_status(status):
    result = False
    if status == GurobiStatus.OPTIMAL:
        result = True
    elif status == GurobiStatus.SUBOPTIMAL:
        result = True
    return result

class GurobiStatus(object):
    LOADED = 1	        # Model is loaded, but no solution information is available.
    OPTIMAL = 2	        # Model was solved to optimality (subject to tolerances), and an optimal solution is available.
    INFEASIBLE = 3	    # Model was proven to be infeasible.
    INF_OR_UNBD = 4	    # Model was proven to be either infeasible or unbounded. To obtain a more definitive conclusion, set the DualReductions parameter to 0 and reoptimize.
    UNBOUNDED = 5	    # Model was proven to be unbounded. Important note: an unbounded status indicates the presence of an unbounded ray that allows the objective to improve without limit. It says nothing about whether the model has a feasible solution. If you require information on feasibility, you should set the objective to zero and reoptimize.
    CUTOFF = 6	        # Optimal objective for model was proven to be worse than the value specified in the Cutoff parameter. No solution information is available.
    ITERATION_LIMIT	= 7 # Optimization terminated because the total number of simplex iterations performed exceeded the value specified in the IterationLimit parameter, or because the total number of barrier iterations exceeded the value specified in the BarIterLimit parameter.
    NODE_LIMIT = 8	    # Optimization terminated because the total number of branch-and-cut nodes explored exceeded the value specified in the NodeLimit parameter.
    TIME_LIMIT = 9	    # Optimization terminated because the time expended exceeded the value specified in the TimeLimit parameter.
    SOLUTION_LIMIT = 10 # Optimization terminated because the number of solutions found reached the value specified in the SolutionLimit parameter.
    INTERRUPTED = 11	# Optimization was terminated by the user.
    NUMERIC = 12	    # Optimization was terminated due to unrecoverable numerical difficulties.
    SUBOPTIMAL = 13	    # Unable to satisfy optimality tolerances; a sub-optimal solution is available.
    IN_PROGRESS = 14    # A non-blocking optimization call was made (by setting the NonBlocking parameter to 1 in a Gurobi Compute Server environment), but the associated optimization run is not yet complete.

    def __init__(self,
                 status=1,
                 sol_count=0,
                 obj_value=GRB.INFINITY,
                 obj_bound=GRB.INFINITY,
                 obj_gap=GRB.INFINITY,
                 runtime_wall_clock=GRB.INFINITY,
                 runtime_gurobi=GRB.INFINITY
                 ):
        self.sol_count = sol_count
        self.status = status
        self.obj_value = obj_value
        self.obj_bound = obj_bound
        self.obj_gap = obj_gap
        self.runtime_wall_clock=runtime_wall_clock
        self.runtime_gurobi=runtime_gurobi


    def _convertInfinity_to_minus_one(self, value):
        if value is GRB.INFINITY:
            return -1
        return value

    def get_objective_value(self):
        return self._convertInfinity_to_minus_one(self.obj_value)

    def get_objective_bound(self):
        return self._convertInfinity_to_minus_one(self.obj_bound)

    def get_mip_gap(self):
        return self._convertInfinity_to_minus_one(self.obj_gap)

    def get_runtime_wall_clock(self):
        return self._convertInfinity_to_minus_one(self.runtime_wall_clock)

    def get_runtime_gurobi(self):
        return self._convertInfinity_to_minus_one(self.runtime_gurobi)

    def has_feasible_status(self):
        return is_feasible_status(self.status)

    def is_feasible(self):
        result = self.sol_count > 0
        return result

    def is_unknown(self):
        return not (self.is_feasible() or self.is_infeasible())

    def is_infeasible(self):
        return is_infeasible_status(self.status)

    def is_optimal(self):
        #print "this IS NOT optimal {} {}".format(self.status, self.solCount)
        if self.status == self.OPTIMAL and self.sol_count > 0:
            return True
        else:
            return False


    def __str__(self):
        return "Status code {};\tObjVal {};\tObjBnd {};\tObjGap {};\truntime (wall_clock) {};\truntime (gurobi)".format(self.status,
                                                                                                                        self.obj_value,
                                                                                                                        self.obj_bound,
                                                                                                                        self.obj_gap,
                                                                                                                        self.runtime_wall_clock,
                                                                                                                        self.runtime_gurobi)


class LogEntry(object):
    '''Simple class capturing the solution state of gurobi at a point in time.

    '''
    def __init__(self, time, node_count, objective_value, objective_bound, solution_count):
        self.time = time
        self.node_count = node_count
        self.objective_value = objective_value
        self.objective_bound = objective_bound
        self.solution_count = solution_count

    def update_entry(self, time, node_count, objective_value, objective_bound, solution_count):
        self.time = time
        self.node_count = node_count
        self.objective_value = objective_value
        self.objective_bound = objective_bound
        self.solution_count = solution_count

    def __str__(self):
        return "Time {};\tObjVal {};\tObjBnd {};\tNC {};\tSC {};".format(self.time, self.objective_value, self.objective_bound, self.node_count, self.solution_count)

class TemporalLog(object):
    '''Represents the temporal solution process of gurobi by enabling the logging at particular points in time.

    '''
    def __init__(self):
        self.log_entries = []
        self.start_time = time.time()
        self.current_entry = -1

    def set_start_time(self, start_time):
        self.start_time = start_time

    def add_log_data(self, node_count, objective_value, objective_bound, solution_count):
        try:
            current_time = time.time()
            time_since_start = current_time - self.start_time
            last_entry = None
            if self.current_entry >= 0:
                last_entry = self.log_entries[self.current_entry]

            if last_entry is None:
                log_entry = LogEntry(time=time_since_start, node_count=node_count, objective_value=objective_value, objective_bound=objective_bound, solution_count=solution_count)
                self.log_entries.append(log_entry)
                self.current_entry += 1

            elif math.floor(time_since_start) - math.floor(last_entry.time) == 0 and last_entry.objective_value == objective_value:
                #if it happened in the same second and the same objective is given, we simply update the other values
                last_entry.update_entry(time=time_since_start, node_count=node_count, objective_value=objective_value, objective_bound=objective_bound, solution_count=solution_count)
            else:
                log_entry = LogEntry(time=time_since_start, node_count=node_count, objective_value=objective_value, objective_bound=objective_bound, solution_count=solution_count)
                self.log_entries.append(log_entry)
                self.current_entry += 1
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(exc_type, exc_tb.tb_lineno)


class ExtractedSolutionData(object):

    CLASS_OPTIMAL = 2
    CLASS_FEASIBLE = 1
    CLASS_INFEASIBLE = -1
    CLASS_UNKNOWN = 0


    def __init__(self):
        self.first_solution_time = None
        self.first_solution = None
        self.solution = None
        self.runtime = None
        self.classification = None

    def read_from_netup_instance_solution(self, netup_instance_solution):
        for log_entry in netup_instance_solution.temporal_log.log_entries:
            if log_entry.solution_count > 0:
                self.first_solution = log_entry.objective_value
                self.first_solution_time = log_entry.time
                break

        self.solution = netup_instance_solution.status.obj_value
        self.runtime = netup_instance_solution.status.runtime_wall_clock

        if netup_instance_solution.status.is_optimal():
            self.classification = self.CLASS_OPTIMAL
        elif netup_instance_solution.status.is_feasible():
            self.classification = self.CLASS_FEASIBLE
        elif netup_instance_solution.status.is_infeasible():
            self.classification = self.CLASS_INFEASIBLE
        else:
            self.netup_instance_solution = self.CLASS_UNKNOWN

    def __str__(self):
        return "{} {} {} {} {}".format(self.first_solution_time, self.first_solution, self.solution, self.runtime, self.classification)


InstanceGenerationParamsTuple = namedtuple("InstanceGenerationParamsTuple", ["nodes",
                                                                             "number_wps",
                                                                             "index"])

class ExtractedExperimentDataStorage(object):


    def __init__(self, original_instance_storage_id):
        '''It's important that the instance_storage_id really corresponds to the InstanceStorage object.

        :param original_instance_storage_id:
        :return:
        '''
        self.instance_storage_id = original_instance_storage_id
        self.gen_params_to_model_to_extracted_data = {}
        self.gen_params_to_original_index = {}
        self.unique_model_configurations = set()
        self.igp_nodes = None
        self.igp_wps = None
        self.igp_index = None


    def add_solution_data(self,
                          instance_index,
                          gen_params,
                          model_configuration_representation,
                          netupdate_solution):


        print "current data storage: \n\t{}".format(self.gen_params_to_model_to_extracted_data)
        print "adding {} {} {}".format(instance_index, gen_params, model_configuration_representation, netupdate_solution)



        gen_params_tuple = InstanceGenerationParamsTuple(nodes=gen_params.nodes, number_wps=gen_params.number_wps, index=gen_params.index)


        unique_model_configuration = None
        for model_configuration in self.unique_model_configurations:
            if model_configuration.decision_variant == model_configuration_representation[0][1] and \
                            model_configuration.use_flow_extension == model_configuration_representation[1][1] and \
                            model_configuration.strong_loop_freedom == model_configuration_representation[2][1]:
                unique_model_configuration = model_configuration
                break

        if unique_model_configuration is None:
            unique_model_configuration= ModelConfiguration(decision_variant=model_configuration_representation[0][1],
                                                           use_flow_extension=model_configuration_representation[1][1],
                                                           strong_loop_freedom=model_configuration_representation[2][1])
            self.unique_model_configurations.add(unique_model_configuration)

        if gen_params_tuple not in self.gen_params_to_model_to_extracted_data:
            self.gen_params_to_model_to_extracted_data[gen_params_tuple] = {}
        if gen_params_tuple not in self.gen_params_to_original_index:
            self.gen_params_to_original_index[gen_params_tuple] = {}

        self.gen_params_to_original_index[gen_params_tuple] = instance_index

        extracted_data = ExtractedSolutionData()
        extracted_data.read_from_netup_instance_solution(netupdate_solution)

        if unique_model_configuration in self.gen_params_to_model_to_extracted_data[gen_params_tuple]:
            print "contained umcs..."
            for umc in self.gen_params_to_model_to_extracted_data[gen_params_tuple]:
                print "\t", umc
            print "new umc: \n\t", unique_model_configuration
            raise Exception("Overwriting result previously already set.")



        self.gen_params_to_model_to_extracted_data[gen_params_tuple][unique_model_configuration] = extracted_data


    def collect_instance_generation_parameters(self):
        nodes = set()
        wps = set()
        index = set()
        for gen_params_tuple in self.gen_params_to_model_to_extracted_data.keys():
            nodes.add(gen_params_tuple.nodes)
            wps.add(gen_params_tuple.number_wps)
            index.add(gen_params_tuple.index)
        self.igp_nodes = [x for x in sorted(nodes)]
        self.igp_wps = [x for x in sorted(wps)]
        self.igp_index = [x for x in sorted(index)]


    def check_completeness_of_data(self):
        list_of_missing_data = []
        for node, wp, index in itertools.product(self.igp_nodes, self.igp_wps, self.igp_index):
            for umc in self.unique_model_configurations:
                if (node, wp, index) not in self.gen_params_to_model_to_extracted_data:
                    list_of_missing_data.append((node, wp, index))
                else:
                    if umc not in self.gen_params_to_model_to_extracted_data[(node, wp, index)]:
                        list_of_missing_data.append(((node, wp, index), (umc)))

        if len(list_of_missing_data) > 0:
            print "Missing the data of the following experiments..."
            for obj in list_of_missing_data:
                print "\t{}".format(obj)
            return False

        return True







if __name__ == '__main__':
    scen = NetworkUpdateInstance()
    scen.generate_randomly(10, 0)
    scen.write_to_file("10_0")
    scen.generate_randomly(10, 1)
    scen.write_to_file("10_1")
    scen.generate_randomly(20, 2)
    scen.write_to_file("20_1")
    scen.generate_randomly(30, 3)
    scen.write_to_file("30_1")
