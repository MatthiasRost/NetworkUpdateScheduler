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

import gurobipy
from gurobipy import GRB

import sys
import traceback
import time

import datamodel as dm


def master_callback(model, where):
    ''' Gurobi callback to save information into temporal log during the execution of Gurobi.

    '''
    try:
        modelcreator = model._modelcreator
        temoral_log = modelcreator.temporal_log

        if where == GRB.callback.MIP:
            # General MIP callback
            nodecnt = model.cbGet(GRB.callback.MIP_NODCNT)
            objbst = model.cbGet(GRB.callback.MIP_OBJBST)
            objbnd = model.cbGet(GRB.callback.MIP_OBJBND)
            solcnt = model.cbGet(GRB.callback.MIP_SOLCNT)
            temoral_log.add_log_data(node_count=nodecnt, objective_value=objbst, objective_bound=objbnd, solution_count=solcnt)

        elif where == GRB.callback.MIPSOL:
            nodecnt = model.cbGet(GRB.callback.MIPSOL_NODCNT)
            objbst = model.cbGet(GRB.callback.MIPSOL_OBJBST)
            objbnd = model.cbGet(GRB.callback.MIPSOL_OBJBND)
            solcnt = model.cbGet(GRB.callback.MIPSOL_SOLCNT)

            temoral_log.add_log_data(node_count=nodecnt, objective_value=objbst, objective_bound=objbnd, solution_count=solcnt)

    except Exception:
        print(sys.exc_info()[0])
        traceback.print_exc()


class ModelCreator(object):
    ''' Class that instantiates a Mixed-Integer Program and solves it to compute optimal network update schedules.

    '''

    def __init__(self, instance, model_configuration, gurobi_settings):
        '''

        :param instance: the network update instance
        :param model_configuration: the model configuration, i.e. which MIP variant shall be employed
        :param gurobi_settings: settings giving bounds on the execution time, the MIP gap etc.
        :return:
        '''
        self.instance = instance
        self.model_configuration = model_configuration

        self.timelimit = gurobi_settings.timelimit
        self.threads = gurobi_settings.threads
        self.mip_gap = gurobi_settings.mip_gap
        self.numeric_focus = gurobi_settings.numeric_focus

        self.rounds = None
        self.pre_rounds =  None
        self.sup_rounds = None

        self.V = self.instance.nodes

        if not self.instance.nodes[len(self.instance.nodes)-1] == self.instance.end:
            raise Exception("The last mentioned node should be the end node!")

        # this assumes that the last node is always the end node!
        self.V_we = self.instance.nodes[0:len(self.instance.nodes) - 1]

        self.E_orig = self.instance.old_edges
        self.E_new = self.instance.new_edges
        self.E_total = self.E_orig + self.E_new
        self.start = self.instance.start
        self.end = self.instance.end

        self.maximal_number_of_rounds = self.instance.rounds


        self.wps = self.instance.wp.values()

        self._construct_index_sets()

        self.model = None

        self.temporal_log = dm.TemporalLog()



    def compute_solution(self):
        ''' Computes a (potentially) optimal network update schedule or decides that none exists.

        :return: a NetworkUpdateInstanceSolution representing the solution
        '''

        if self.model is None:
            self._construct_model()

        self.model._modelcreator = self

        self.model.setParam("Threads", self.threads)
        self.model.setParam("TimeLimit", self.timelimit)
        self.model.setParam("MIPGap", self.mip_gap)
        self.model.setParam("NumericFocus", self.numeric_focus)
        #self.model.setParam("Presolve", 0)

        self.model.optimize(master_callback)

        status = self.model.getAttr("Status")
        objVal = None
        objBound = GRB.INFINITY
        objGap = GRB.INFINITY
        solutionCount = self.model.getAttr("SolCount")
        runtime = self.model.getAttr("Runtime")



        if solutionCount > 0:
            objVal = self.model.getAttr("ObjVal")
            #interestingly, MIPGap and ObjBound cannot be accessed when there are no variables and the MIP is infeasible..
            objGap = self.model.getAttr("MIPGap")

        if not dm.is_infeasible_status(status):
            objBound = self.model.getAttr("ObjBound")

        self.temporal_log.add_log_data(node_count=self.model.getAttr("NodeCount"), objective_value=objVal, objective_bound=objBound, solution_count=solutionCount)

        self.status = dm.GurobiStatus(status=status,
                                      sol_count=solutionCount,
                                      obj_value=objVal,
                                      obj_gap=objGap,
                                      obj_bound=objBound,
                                      runtime_wall_clock=time.time() - self.temporal_log.start_time,
                                      runtime_gurobi=runtime)

        solution_schedule = None
        if self.status.is_feasible():
            solution_schedule = self.get_solution_schedule()

        result = dm.NetworkUpdateInstanceSolution(status=self.status, temporal_log=self.temporal_log, solution_schedule=solution_schedule)

        return result


    # def adopt_fixings(self):
    #     for round in self.instance.fixings.keys():
    #         for switch in self.instance.fixings[round]:
    #             self.model.addConstr(self.var_upgrade_switch_in_round[round][switch] == 1.0)
    #
    #
    # def set_fixings_according_to_result(self):
    #     if not self.status.is_feasible():
    #         raise Exception("This clearly is not possible!")
    #
    #     self.instance.fixings = {}
    #     for r in self.rounds:
    #         self.instance.fixings[r] = []
    #         for v in self.V_we:
    #             if self.var_upgrade_switch_in_round[r][v].X > 0.5:
    #                 self.instance.fixings[r].append(v)

    def get_solution_schedule(self):
        '''

        :return: a solution schedule as a dictionary mapping rounds to lists of nodes being updated
        '''
        if not self.status.is_feasible():
            raise Exception("This clearly is not possible!")

        solution_schedule = {}
        for r in self.rounds:
            solution_schedule[r] = []
            for v in self.V_we:
                if self.var_upgrade_switch_in_round[r][v].X > 0.5:
                    solution_schedule[r].append(v)

        return solution_schedule

    def _construct_index_sets(self):
        self.rounds = [(x+1) for x in range(self.instance.rounds)]
        self.pre_rounds =  [x for x in range(self.instance.rounds)]
        self.sup_rounds = [x for x in range(self.instance.rounds + 1)]

        self.outgoing_edges = {}
        self.incoming_edges = {}

        for v in self.V:
            self.outgoing_edges[v] = []
            self.incoming_edges[v] = []

        for (tail, head) in self.E_total:
            self.outgoing_edges[tail].append((tail,head))
            self.incoming_edges[head].append((tail,head))

        for v in self.V:
            print "node {}; incoming: {}; outgoing: {}".format(v, self.incoming_edges[v], self.outgoing_edges[v])

        self.new_edge_at = {}
        for (tail, head) in self.E_new:
            self.new_edge_at[tail] = (tail, head)


    def _construct_model(self):
        if self.model is None:
            self.model = gurobipy.Model("NetworkUpdate")
        self._construct_index_sets()
        self._construct_variables()
        self.model.update()
        self._construct_constraints()
        self._construct_objective()


    def _construct_variables(self):
        self.var_upgrade_switch_in_round = {}
        for r in self.rounds:
            self.var_upgrade_switch_in_round[r] = {}
            for v in self.V_we:
                self.var_upgrade_switch_in_round[r][v] = self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.BINARY, name="switch_upgrade_{}_{}".format(r, v))

        self.model.update()
        for r in self.rounds:
            for v in self.V_we:
                self.var_upgrade_switch_in_round[r][v].BranchPriority = 100

        self.var_edge_exists = {}
        for r in self.sup_rounds:
            self.var_edge_exists[r] = {}
            for (tail,head) in self.E_total:
                self.var_edge_exists[r][(tail,head)] = self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.CONTINUOUS, name="edge_exists_{}_{}_{}".format(r, tail,head))

        self.var_edge_exists_transient = {}
        for r in self.rounds:
            self.var_edge_exists_transient[r] = {}
            for (tail,head) in self.E_total:
                self.var_edge_exists_transient[r][(tail,head)] = self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.CONTINUOUS, name="edge_exists_transient_{}_{}_{}".format(r, tail,head))

        if not self.model_configuration.strong_loop_freedom:
            self.var_node_reachable = {}
            for r in self.rounds:
                self.var_node_reachable[r] = {}
                for v in self.V:
                    self.var_node_reachable[r][v] = self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.CONTINUOUS, name="node_reachable_{}_{}".format(r, v))

        if len(self.wps) > 0:
            self.var_node_reachable_wowp = {}

        for wp in self.wps:
            self.var_node_reachable_wowp[wp] = {}
            for r in self.rounds:
                self.var_node_reachable_wowp[wp][r] = {}
                for v in self.V:
                    self.var_node_reachable_wowp[wp][r][v] = self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.CONTINUOUS, name="node_reachable_wowp_{}_{}_{}".format(r, wp, v))

        if self.model_configuration.use_flow_extension:
            self.var_flow = {}
            for r in self.sup_rounds:
                self.var_flow[r] = {}
                for (tail, head) in self.E_total:
                    self.var_flow[r][(tail,head)] = self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.CONTINUOUS, name="flow_{}_{}_{}".format(r, tail, head))

        self.var_node_level = {}
        for r in self.rounds:
            self.var_node_level[r] = {}
            for v in self.V:
                self.var_node_level[r][v] = self.model.addVar(lb=0.0, ub=self.instance.number_of_nodes - 1, obj=0.0, vtype=GRB.CONTINUOUS, name="node_level_{}_{}".format(r, v))

        self.var_upgrade_in_round = {}
        for r in self.rounds:
            self.var_upgrade_in_round[r] = self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.CONTINUOUS, name="upgrade_in_round_{}".format(r))

        self.var_number_of_used_rounds = self.model.addVar(lb=0.0, ub=self.instance.rounds, obj=0.0, vtype=GRB.CONTINUOUS, name="number_of_used_rounds")


    def _construct_constraints(self):

        for node in self.V_we:
            expr = gurobipy.LinExpr()
            expr.addTerms([1.0]*self.maximal_number_of_rounds, [self.var_upgrade_switch_in_round[r][node] for r in self.rounds])
            self.model.addConstr(expr, GRB.EQUAL, 1.0, name="upgrade_all_nodes_{}".format(node))

        if self.model_configuration.decision_variant:
            for r in self.rounds:
                expr  = gurobipy.LinExpr()
                expr.addTerms([1.0]*(len(self.V_we)), [self.var_upgrade_switch_in_round[r][node] for node in self.V_we])
                self.model.addConstr(expr, GRB.EQUAL, 1.0, name="exactly_one_update_per_round_{}".format(r))

        for r in self.sup_rounds:
            for (tail, head) in self.E_orig:
                expr = gurobipy.LinExpr()
                expr.addTerms(1.0, self.var_edge_exists[r][(tail,head)])
                expr.addTerms([1.0]*r, [self.var_upgrade_switch_in_round[x][tail] for x in range(1, r+1)])
                self.model.addConstr(expr, GRB.EQUAL, 1.0, name="edge_exists_orig_{}_{}_{}".format(r, tail, head))

        for r in self.sup_rounds:
            for (tail, head) in self.E_new:
                expr = gurobipy.LinExpr()
                expr.addTerms(1.0, self.var_edge_exists[r][(tail,head)])
                expr.addTerms([-1.0]*r, [self.var_upgrade_switch_in_round[x][tail] for x in range(1, r+1)])
                self.model.addConstr(expr, GRB.EQUAL, 0.0, name="edge_exists_new_{}_{}_{}".format(r, tail, head))

        if not self.model_configuration.strong_loop_freedom:
            for r in self.rounds:
                self.model.addConstr(self.var_node_reachable[r][self.start], GRB.EQUAL, 1.0, name="set_node_reachable_start_{}".format(r))

            for r in self.rounds:
                for (tail, head) in self.E_total:
                    expr = gurobipy.LinExpr()
                    expr.addTerms( 1.0, self.var_node_reachable[r][head])
                    expr.addTerms(-1.0, self.var_node_reachable[r][tail])
                    expr.addTerms(-1.0, self.var_edge_exists[r][(tail,head)])
                    self.model.addConstr(expr, GRB.GREATER_EQUAL, -1.0, name="set_node_reachable_other_{}_{}_{}".format(r,tail,head))

            for r in self.rounds:
                for (tail, head) in self.E_total:
                    expr = gurobipy.LinExpr()
                    expr.addTerms( 1.0, self.var_node_reachable[r][head])
                    expr.addTerms(-1.0, self.var_node_reachable[r][tail])
                    expr.addTerms(-1.0, self.var_edge_exists[r-1][(tail,head)])
                    self.model.addConstr(expr, GRB.GREATER_EQUAL, -1.0, name="set_node_reachable_other_2_{}_{}_{}".format(r,tail,head))

        # FORBIDDING BYPASSING OF WAYPOINTS

        for wp in self.wps:
            for r in self.rounds:
                self.model.addConstr(self.var_node_reachable_wowp[wp][r][self.start], GRB.EQUAL, 1.0, name="set_node_reachable_wowp_start_{}_{}".format(r, wp))

        for wp in self.wps:
            for r in self.rounds:
                for (tail,head) in self.E_total:
                    if tail == wp or head == wp:
                        continue
                    expr = gurobipy.LinExpr()
                    expr.addTerms( 1.0, self.var_node_reachable_wowp[wp][r][head])
                    expr.addTerms(-1.0, self.var_node_reachable_wowp[wp][r][tail])
                    expr.addTerms(-1.0, self.var_edge_exists[r][(tail,head)])
                    self.model.addConstr(expr, GRB.GREATER_EQUAL, -1.0, name="set_node_reachable_wowp_other_1___{}_{}_{}_{}".format(r, wp, tail, head))

        for wp in self.wps:
            for r in self.rounds:
                for (tail,head) in self.E_total:
                    if tail == wp or head == wp:
                        continue
                    expr = gurobipy.LinExpr()
                    expr.addTerms( 1.0, self.var_node_reachable_wowp[wp][r][head])
                    expr.addTerms(-1.0, self.var_node_reachable_wowp[wp][r][tail])
                    expr.addTerms(-1.0, self.var_edge_exists[r-1][(tail,head)])
                    self.model.addConstr(expr, GRB.GREATER_EQUAL, -1.0, name="set_node_reachable_wowp_other_2____{}_{}_{}_{}".format(r, wp, tail, head))

        for wp in self.wps:
            for r in self.rounds:
                self.model.addConstr(self.var_node_reachable_wowp[wp][r][self.instance.end], GRB.EQUAL, 0.0, name="forbid_bypassing_the_wp_{}_{}".format(r, wp))

        # FORBIDDING CYCLES

        for r in self.rounds:
            for (tail, head) in self.E_total:
                expr = gurobipy.LinExpr()
                if self.model_configuration.strong_loop_freedom:
                    expr.addTerms( 1.0, self.var_edge_exists_transient[r][(tail,head)])
                    expr.addTerms(-1.0, self.var_edge_exists[r-1][(tail,head)])
                    self.model.addConstr(expr, GRB.GREATER_EQUAL, 0.0, name="set_edge_exists_transient_1_strong_{}_{}_{}".format(r, tail, head))
                else:
                    expr.addTerms( 1.0, self.var_edge_exists_transient[r][(tail,head)])
                    expr.addTerms(-1.0, self.var_edge_exists[r-1][(tail,head)])
                    expr.addTerms(-1.0, self.var_node_reachable[r][tail])
                    self.model.addConstr(expr, GRB.GREATER_EQUAL, -1.0, name="set_edge_exists_transient_1_weak_{}_{}_{}".format(r, tail, head))

        for r in self.rounds:
            for (tail, head) in self.E_total:
                expr = gurobipy.LinExpr()
                if self.model_configuration.strong_loop_freedom:
                    expr.addTerms( 1.0, self.var_edge_exists_transient[r][(tail,head)])
                    expr.addTerms(-1.0, self.var_edge_exists[r][(tail,head)])
                    self.model.addConstr(expr, GRB.GREATER_EQUAL, 0.0, name="set_edge_exists_transient_2_strong_{}_{}_{}".format(r, tail, head))
                else:
                    expr.addTerms( 1.0, self.var_edge_exists_transient[r][(tail,head)])
                    expr.addTerms(-1.0, self.var_edge_exists[r][(tail,head)])
                    expr.addTerms(-1.0, self.var_node_reachable[r][tail])
                    self.model.addConstr(expr, GRB.GREATER_EQUAL, -1.0, name="set_edge_exists_transient_2_weak_{}_{}_{}".format(r, tail, head))

        for r in self.rounds:
            for (tail,head) in self.E_total:
                expr = gurobipy.LinExpr()
                n = float(self.instance.number_of_nodes - 1)
                expr.addTerms(   (n-1), self.var_edge_exists_transient[r][(tail,head)])
                expr.addTerms(-1.0, self.var_node_level[r][head])
                expr.addTerms( 1.0, self.var_node_level[r][tail])
                self.model.addConstr(expr, GRB.LESS_EQUAL, n-2.0, name="forbid_cycles_{}_{}_{}".format(r, tail, head))

        for r in self.rounds:
            self.model.addConstr(self.var_node_level[r][self.start], GRB.EQUAL, 0.0, name="forbid_cycles_init_{}".format(r))


        # FLOW EXTENSION

        if self.model_configuration.use_flow_extension:
            for r in self.rounds:
                expr  = gurobipy.LinExpr()
                for (tail, head) in self.outgoing_edges[self.start]:
                    expr.addTerms(1.0, self.var_flow[r][(tail, head)])
                self.model.addConstr(expr, GRB.EQUAL, 1.0, name="flow_must_be_sent_{}".format(r, self.start))

            for r in self.sup_rounds:
                for v in self.V_we:
                    if v == self.start:
                        continue
                    if v == self.end:
                        continue
                    expr  = gurobipy.LinExpr()
                    for (tail, head) in self.outgoing_edges[v]:
                        expr.addTerms(1.0, self.var_flow[r][(tail, head)])
                    for (tail, head) in self.incoming_edges[v]:
                        expr.addTerms(-1.0, self.var_flow[r][(tail, head)])

                    self.model.addConstr(expr, GRB.EQUAL, 0.0, name="flow_preservation_{}_{}".format(r,v))

            for r in self.sup_rounds:
                for (tail,head) in self.E_total:
                    expr  = gurobipy.LinExpr()
                    expr.addTerms(1.0, self.var_flow[r][(tail, head)])
                    expr.addTerms(-1.0, self.var_edge_exists[r][(tail,head)])

                    self.model.addConstr(expr, GRB.LESS_EQUAL, 0.0, name="flow_bounded_by_edges_existence_{}_{}_{}".format(r, tail, head))


            if len(self.wps) > 0:
                for r in self.sup_rounds:
                    for wp in self.wps:
                        expr  = gurobipy.LinExpr()
                        for (tail, head) in self.incoming_edges[wp]:
                            expr.addTerms(1.0, self.var_flow[r][(tail, head)])
                        self.model.addConstr(expr, GRB.EQUAL, 1.0, name="flow_from_start_must_reach_wp_{}_{}".format(r, wp))
                    expr  = gurobipy.LinExpr()
                    for (tail, head) in self.incoming_edges[wp]:
                        expr.addTerms(1.0, self.var_flow[r][(tail, head)])
                    self.model.addConstr(expr, GRB.EQUAL, 1.0, name="flow_from_start_must_reach_end_{}".format(r))

            if not self.model_configuration.strong_loop_freedom:
                #additionally bound the node reachability by the flow
                for r in self.rounds:
                    for v in self.V_we:
                        if v == self.start:
                            continue
                        expr  = gurobipy.LinExpr()
                        for (tail, head) in self.incoming_edges[v]:
                            expr.addTerms(1.0, self.var_flow[r][(tail, head)])
                        expr.addTerms(-1.0, self.var_node_reachable[r][v])

                        self.model.addConstr(expr, GRB.LESS_EQUAL, 0.0, name="bound_node_reachability_by_flow_from_below_1".format(r, v))

                        expr  = gurobipy.LinExpr()
                        for (tail, head) in self.incoming_edges[v]:
                            expr.addTerms(1.0, self.var_flow[r-1][(tail, head)])
                        expr.addTerms(-1.0, self.var_node_reachable[r][v])

                        self.model.addConstr(expr, GRB.LESS_EQUAL, 0.0, name="bound_node_reachability_by_flow_from_below_2".format(r, v))


        # FOR THE OBJECTIVE

        for r in self.rounds:
            for node in self.V_we:
                expr = gurobipy.LinExpr()
                expr.addTerms( 1.0, self.var_upgrade_in_round[r])
                expr.addTerms(-1.0, self.var_upgrade_switch_in_round[r][node])
                self.model.addConstr(expr, GRB.GREATER_EQUAL, 0.0, name="select_upgrade_{}_{}".format(r, node))

        for r in self.rounds:
            expr = gurobipy.LinExpr()
            expr.addTerms(1.0, self.var_number_of_used_rounds)
            expr.addTerms(-float(r), self.var_upgrade_in_round[r])
            self.model.addConstr(expr, GRB.GREATER_EQUAL, 0.0, name="set_number_of_used_rounds_{}".format(r))


    def _construct_objective(self):
        self.model.setObjective(self.var_number_of_used_rounds, GRB.MINIMIZE)
