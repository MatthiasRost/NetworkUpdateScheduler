import os
import matplotlib.pyplot as plt
import cPickle
import itertools
import numpy as np

from . import datamodel as datamodel

USE_SHORT_NOTATION = True


def get_model_configuration_description(model_configuration):
    result = []
    if model_configuration.decision_variant:
        result.append("D")
    else:
        result.append("-")

    if model_configuration.strong_loop_freedom:
        result.append("S")
    else:
        result.append("R")

    if model_configuration.use_flow_extension:
        result.append("F")
    else:
        result.append("-")
    return "".join(result)


class PlottingData(object):
    ''' Container used for plotting, which contains both the solution dictionary as well as further information
        on the contained scenarios (number of nodes etc.)

    '''

    def __init__(self, eeds):
        self.eeds = eeds
        self.eeds.collect_instance_generation_parameters()
        self.solution_dict = self.eeds.gen_params_to_model_to_extracted_data

        self.nodes = sorted(self.eeds.igp_nodes)
        self.wps = sorted(self.eeds.igp_wps)
        self.index = sorted(self.eeds.igp_index)
        self.max_index = self.index[-1]

        self.max_number_of_rounds = max(self.nodes) - 1
        self.rounds = [x for x in range(1, self.max_number_of_rounds)]
        self.model_configurations = sorted(self.solution_dict.values()[0].keys(),
                                           key=lambda mc: get_model_configuration_description(mc))


SLF = "S"
RLF = "R"


def calculate_ecdf_values(plotting_data):
    ''' Computes for each scenario and both RLF and SLF the optimal number of rounds
        and the best feasible number of rounds computed by any of the non-decision algorithms.

    :param plotting_data:
    :return: dictionary containing for each scenario and both SLF and RLF a tuple indicating the optimal number of rounds
             and the best feasible number of rounds found
    '''

    pd = plotting_data
    solution_dict = pd.solution_dict

    result_best_known_number_of_rounds = {scen_param:
                                              {SLF: (-1, -1), RLF: (-1, -1)}
                                          for scen_param in solution_dict.keys()}

    model_configurations = plotting_data.model_configurations

    for scenario_parameter in solution_dict.keys():
        model_to_sol_dict = solution_dict[scenario_parameter]

        # extract optimal number of rounds and best feasible number of rounds under SLF and RLF
        o_r = -1
        o_s = -1
        f_r = -1
        f_s = -1

        for mc in model_configurations:

            if not mc.decision_variant:
                if model_to_sol_dict[mc].classification == datamodel.ExtractedSolutionData.CLASS_OPTIMAL:
                    if mc.strong_loop_freedom:
                        o_s = model_to_sol_dict[mc].solution
                        f_s = model_to_sol_dict[mc].solution
                    else:
                        o_r = model_to_sol_dict[mc].solution
                        f_r = model_to_sol_dict[mc].solution

                elif model_to_sol_dict[mc].classification == datamodel.ExtractedSolutionData.CLASS_FEASIBLE:
                    if mc.strong_loop_freedom:
                        if model_to_sol_dict[mc].solution < f_s:
                            f_s = model_to_sol_dict[mc].solution
                    else:
                        if model_to_sol_dict[mc].solution < f_r:
                            f_r = model_to_sol_dict[mc].solution

        result_best_known_number_of_rounds[scenario_parameter][SLF] = (o_s, f_s)
        result_best_known_number_of_rounds[scenario_parameter][RLF] = (o_r, f_r)

    return result_best_known_number_of_rounds


def calculate_boxplot_runtime_values(plotting_data, timelimit=1000):
    ''' Computes for each number of nodes and each number of waypoints and each model configuration the list of runtimes
        to either establish infeasibility or to find the first solution.

    :param plotting_data:
    :param timelimit: the time limit after which the execution was aborted
    :return:
    '''
    solution_dict = plotting_data.solution_dict

    result_time_until_infeasibility_or_first_solution = {
        (nodes, n_wps): {
            mc: (list(), list()) for mc in plotting_data.model_configurations}
        for nodes, n_wps in
        itertools.product(plotting_data.nodes,
                          plotting_data.wps)}

    for scenario_parameter in solution_dict.keys():
        model_to_sol_dict = solution_dict[scenario_parameter]

        for mc in plotting_data.model_configurations:
            inf, first = result_time_until_infeasibility_or_first_solution[
                (scenario_parameter.nodes, scenario_parameter.number_wps)][mc]

            if model_to_sol_dict[mc].classification == datamodel.ExtractedSolutionData.CLASS_INFEASIBLE:
                inf.append(model_to_sol_dict[mc].runtime)
            else:
                if model_to_sol_dict[mc].first_solution_time is not None:
                    first.append(model_to_sol_dict[mc].first_solution_time)
                else:
                    first.append(timelimit)

            result_time_until_infeasibility_or_first_solution[
                (scenario_parameter.nodes, scenario_parameter.number_wps)][mc] = (inf, first)

    return result_time_until_infeasibility_or_first_solution


def calculate_barplot_values_and_aggregate_quality(plotting_data):
    ''' Computes for each number of nodes and each number of waypoints and each modelconfiguration the count of
        classifications across the scenarios.

    :param plotting_data:
    :return:
    '''

    solution_dict = plotting_data.solution_dict

    result_aggregated_classification_per_mc = {
        (nodes, n_wps): {
            mc: (0, 0, 0, 0) for mc in plotting_data.model_configurations
        } for nodes, n_wps in
        itertools.product(plotting_data.nodes,
                          plotting_data.wps)}
    model_configurations = plotting_data.model_configurations

    for scenario_parameter in solution_dict.keys():
        model_to_sol_dict = solution_dict[scenario_parameter]

        for mc in model_configurations:
            opt, feas, unk, inf = \
                result_aggregated_classification_per_mc[(scenario_parameter.nodes, scenario_parameter.number_wps)][mc]
            if model_to_sol_dict[mc].classification == datamodel.ExtractedSolutionData.CLASS_OPTIMAL:
                result_aggregated_classification_per_mc[(scenario_parameter.nodes, scenario_parameter.number_wps)][
                    mc] = (
                    opt + 1, feas, unk, inf)
            elif model_to_sol_dict[mc].classification == datamodel.ExtractedSolutionData.CLASS_FEASIBLE:
                result_aggregated_classification_per_mc[(scenario_parameter.nodes, scenario_parameter.number_wps)][
                    mc] = (
                    opt, feas + 1, unk, inf)
            elif model_to_sol_dict[mc].classification == datamodel.ExtractedSolutionData.CLASS_UNKNOWN:
                result_aggregated_classification_per_mc[(scenario_parameter.nodes, scenario_parameter.number_wps)][
                    mc] = (
                    opt, feas, unk + 1, inf)
            elif model_to_sol_dict[mc].classification == datamodel.ExtractedSolutionData.CLASS_INFEASIBLE:
                result_aggregated_classification_per_mc[(scenario_parameter.nodes, scenario_parameter.number_wps)][
                    mc] = (
                    opt, feas, unk, inf + 1)
            else:
                raise ValueError("Solution state could not be determined")

    return result_aggregated_classification_per_mc


def calculate_lineplot_values_and_aggregate_quality(plotting_data):
    ''' Computes for each number of nodes and each number of waypoints the (non-disjoint) classification data:
            - whether an optimal solution was found for SLF and RLF
            - whether a feasible solution was determined overall
            - whether infeasibility was established
            - otherwise: whether it is unknown whether the scenario can be solved

    :param plotting_data:
    :return:
    '''
    solution_dict = plotting_data.solution_dict

    result_aggregated_classification = {(nodes, n_wps): (0, 0, 0, 0, 0) for nodes, n_wps in
                                        itertools.product(plotting_data.nodes,
                                                          plotting_data.wps)}
    model_configurations = plotting_data.model_configurations

    for scenario_parameter in solution_dict.keys():
        model_to_sol_dict = solution_dict[scenario_parameter]

        opt_w, opt_s, feas, unk, inf = result_aggregated_classification[
            (scenario_parameter.nodes, scenario_parameter.number_wps)]

        o_w = False
        o_s = False
        f = False
        u = False
        i = False

        for mc in model_configurations:

            if not mc.decision_variant:
                if model_to_sol_dict[mc].classification == datamodel.ExtractedSolutionData.CLASS_OPTIMAL:
                    if mc.strong_loop_freedom:
                        o_s = True
                    else:
                        o_w = True
                    f = True
                elif model_to_sol_dict[mc].classification == datamodel.ExtractedSolutionData.CLASS_FEASIBLE:
                    f = True
            else:
                if model_to_sol_dict[mc].classification == datamodel.ExtractedSolutionData.CLASS_OPTIMAL:
                    f = True

            if model_to_sol_dict[mc].classification == datamodel.ExtractedSolutionData.CLASS_UNKNOWN:
                u = True

            if model_to_sol_dict[mc].classification == datamodel.ExtractedSolutionData.CLASS_INFEASIBLE:
                i = True

        if (o_w or o_s or f) and (i):
            raise RuntimeWarning("It seems that a scenario is both solvable but yet infeasible.\n"
                                 "This should -- in general -- not happen, but might be due to some numerical instabilities.\n"
                                 "Please check the scenario solutions manually: {}".format(scenario_parameter))

        if o_w or o_s or f:
            if o_w:
                opt_w += 1
            if o_s:
                opt_s += 1
            feas += 1
        else:
            if i:
                inf += 1
            elif u:
                unk += 1

        result_aggregated_classification[(scenario_parameter.nodes, scenario_parameter.number_wps)] = (
            opt_w, opt_s, feas, unk, inf)

    return result_aggregated_classification


def load_pickle(filename):
    with open(filename, "r") as f:
        return cPickle.load(f)


def remove_spaces(string):
    return "_".join(string.split()).lower()


class DefaultFigureSpec(object):
    ''' Class to store plot specifications. Used only to easily change parameters across different plots
        and to not need to search the places where these parameters are used.
    '''

    def __init__(self):
        self.fig_size = (6, 4.5)
        self.title_fs = 16
        self.sup_title_fs = 18
        self.sub_title_fs = 16
        self.x_axis_label_fs = 15
        self.y_axis_label_fs = 15
        self.x_axis_tick_label_fs = 14
        self.y_axis_tick_label_fs = 14
        self.legend_fs = 14
        self.suptitle_location = {"x": 0.37, "y": 0.825}
        self.subplot_adjust = {
            "top": 0.7,
            "bottom": 0.2,
            "left": 0.2,
            "right": 0.6,
            "wspace": 0.2,
            "hspace": 0.2
        }
        self.subtitle_location = {"x": 0.5, "y": 0.015}


class BarPlotSpec(DefaultFigureSpec):

    def __init__(self):
        super(BarPlotSpec, self).__init__()
        self.x_axis_tick_label_fs = 14


class LinePlotSpec(DefaultFigureSpec):

    def __init__(self):
        super(LinePlotSpec, self).__init__()


class BoxPlotSpec(DefaultFigureSpec):

    def __init__(self):
        super(BoxPlotSpec, self).__init__()
        self.x_axis_tick_label_fs = 10
        self.y_axis_tick_label_fs = 10
        self.subplot_adjust = {
            "top": 0.8,
            "bottom": 0.15,
            "left": 0.1,
            "right": 0.95,
            "wspace": 0.0,
            "hspace": 0.2
        }
        self.fig_size = (7, 2.5)
        self.suptitle_location["x"] = 0.5
        self.suptitle_location["y"] = 0.97
        self.sup_title_fs = 12.8
        self.sub_title_fs = 11.5
        self.subtitle_location = {"x": 0.5, "y": 0.015}


class ECDFFigureSpec(BoxPlotSpec):

    def __init__(self):
        super(ECDFFigureSpec, self).__init__()
        self.fig_size = (7.0, 2.0)
        self.title_fs = 12.8
        self.subplot_adjust = {
            "top": 0.88,
            "bottom": 0.2,
            "left": 0.1,
            "right": 0.95,
            "wspace": 0.2,
            "hspace": 0.2
        }
        self.y_axis_label_fs = 11.5
        self.sub_title_fs = 11.5
        self.legend_fs = 11.5


def save_plot_and_close(filename, close=True):
    print "\tSaving plot to {}".format(filename)
    folder = os.path.dirname(filename)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    plt.savefig(filename)
    if close:
        plt.close()


def plot_ecdf_of_number_of_rounds_used_for_SLF_and_RLF(plotting_data,
                                                       nodes_list_to_plot,
                                                       file_name="quality_15_1",
                                                       plot_path="./plots/",
                                                       fig_spec=None):
    ''' Plots ECDF of used rounds when for both SLF and RLF optimal values are known.

    :param plotting_data:
    :param nodes_list_to_plot:
    :param file_name:
    :param plot_path:
    :param max_x:
    :param fig_spec:
    :return:
    '''
    if len(nodes_list_to_plot) != 3:
        raise ValueError("This function was statically coded to only accept exactly 3 node numbers.")
    if fig_spec is None:
        fig_spec = ECDFFigureSpec()

    fig, ax = plt.subplots(figsize=fig_spec.fig_size)
    ax.set_title("Comparison of Optimal Number of Rounds", fontsize=fig_spec.title_fs)
    fig.subplots_adjust(**fig_spec.subplot_adjust)

    best_known_number_of_rounds = calculate_ecdf_values(plotting_data)

    colors = {nodes_list_to_plot[0]: "0.6", nodes_list_to_plot[1]: "0.3", nodes_list_to_plot[2]: "0.0"}
    linestyles_new = {"OS": {nodes_list_to_plot[0]: "-", nodes_list_to_plot[1]: "-", nodes_list_to_plot[2]: "-"},
                      "OR": {nodes_list_to_plot[0]: "--", nodes_list_to_plot[1]: "-.", nodes_list_to_plot[2]: ":"},
                      "FS": ':', "FR": '-.'}

    max_round = -1

    for nodes in nodes_list_to_plot:

        observed_rounds = {"OS": {}, "OR": {}}

        for key in observed_rounds.keys():
            for r in plotting_data.rounds:
                observed_rounds[key][r] = 0

        for wp in plotting_data.wps:
            for index in plotting_data.index:

                o_s, f_s = best_known_number_of_rounds[(nodes, wp, index)][SLF]
                o_r, f_r = best_known_number_of_rounds[(nodes, wp, index)][RLF]

                # only count it if for both SLF and RLF optimal solutions have been found
                if o_s != -1 and o_r != -1:
                    int_round_os = int(round(float(o_s)))
                    int_round_or = int(round(float(o_r)))
                    observed_rounds["OS"][int_round_os] += 1
                    observed_rounds["OR"][int_round_or] += 1
                    max_round = max(max_round, int_round_or, int_round_os)

        # norming it
        count_o = 0
        for r in plotting_data.rounds:
            count_o += observed_rounds["OS"][r]

        for r in plotting_data.rounds:
            observed_rounds["OS"][r] /= float(count_o)
            observed_rounds["OR"][r] /= float(count_o)

        def get_label_line_quality(classifier):
            if classifier == "OS":
                return r"SLF," + str(nodes)
            if classifier == "OR":
                return r"RLF," + str(nodes)

        order = ["OR", "OS"]  # , "FR", "FS"

        for key in order:
            x = []
            y = []
            cum = 0.0
            for r in plotting_data.rounds:
                x.extend([r, r + 1.0])
                cum += observed_rounds[key][r]
                y.extend([cum, cum])

            ax.plot(x, y, color=colors[nodes], linestyle=linestyles_new[key][nodes], label=get_label_line_quality(key),
                    linewidth=2.5, alpha=0.95)

    ax.set_ylim(-0.02, 1.02)
    ax.set_xlim(left=2, right=max_round)
    ax.set_ylabel("ECDF [%]", fontsize=fig_spec.y_axis_label_fs)
    ax.set_xticks([x for x in range(2, max_round+1)], minor=False)
    ax.set_xticklabels(["{}".format(x) for x in range(2, max_round+1)])

    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0], minor=False)
    ax.set_yticklabels(["0", "20", "40", "60", "80", "100"])
    ax.set_axisbelow(True)
    ax.grid(True)

    gridlines = ax.get_xgridlines() + ax.get_ygridlines()
    for line in gridlines:
        line.set_linestyle(':')
        line.set_linewidth(0.66)
        line.set_color("0.5")

    fig.text(0.5, 0.01, 'rounds', ha='center', fontsize=fig_spec.sub_title_fs)
    handles, labels = ax.get_legend_handles_labels()

    def flip(items, ncol):
        return itertools.chain(*[items[i::ncol] for i in range(ncol)])

    plt.legend(flip(handles, 2), flip(labels, 2), loc=4, ncol=2, fontsize=fig_spec.legend_fs)
    plot_file = os.path.join(plot_path, "{}.pdf".format(remove_spaces(file_name)))
    save_plot_and_close(plot_file)


def plot_boxplot_comparison_of_different_modelconfigurations(plotting_data,
                                                             time_until_infeasibility_or_first_solution,
                                                             runtime_to_plot,
                                                             nodes_list_to_plot,
                                                             file_name="quality_30_1",
                                                             plot_path="./plots/",
                                                             fig_spec=None
                                                             ):
    ''' Plots runtime comparisons using boxplots for the different model configurations.

    :param plotting_data:
    :param time_until_infeasibility_or_first_solution:
    :param runtime_to_plot:
    :param nodes_list_to_plot:
    :param file_name:
    :param plot_path:
    :param fig_spec:
    :return:
    '''
    if runtime_to_plot not in ["inf", "first"]:
        raise ValueError("Don't know how to plot this: {}".format(runtime_to_plot))

    if len(nodes_list_to_plot) != 3:
        raise ValueError("This function was statically coded to only accept exactly 3 node numbers.")

    suptitle_title = None
    aggregated_values_index = None
    if runtime_to_plot == "inf":
        suptitle_title = "Runtime Infeasibility Detection"
        aggregated_values_index = 0
    elif runtime_to_plot == "first":
        suptitle_title = "Runtime First Solution"
        aggregated_values_index = 1

    solution_dict = plotting_data.solution_dict
    if fig_spec is None:
        fig_spec = BoxPlotSpec()
    fig, axes = plt.subplots(ncols=len(plotting_data.model_configurations), figsize=fig_spec.fig_size, sharey=True)

    fig.suptitle(suptitle_title, fontsize=fig_spec.sup_title_fs, **fig_spec.suptitle_location)

    fig.subplots_adjust(**fig_spec.subplot_adjust)

    first = True

    for mc, ax in zip(plotting_data.model_configurations, axes):

        if first:
            ax.set_ylabel("runtime [s]", fontsize=fig_spec.y_axis_label_fs)
            first = False

        ax.set_title(get_model_configuration_description(mc))

        collection_of_values = [[] for nodes_number in nodes_list_to_plot]

        for wp in plotting_data.wps:
            for index, nodes_number in enumerate(nodes_list_to_plot):
                collection_of_values[index].extend(
                    time_until_infeasibility_or_first_solution[(nodes_number, wp)][mc][aggregated_values_index])

        # pos = [0.5 + 0.5*i for i in range(len(collection_of_values))]
        pos = [0.125, 1., 1.875]
        widths = [0.4, 0.4, 0.4]
        bp = ax.boxplot(collection_of_values, positions=pos, patch_artist=True, widths=widths)  #

        colors = ["#999999", "#CCCCCC", "#FFFFFF"]
        for box, color in zip(bp['boxes'], colors):
            # change outline color
            box.set(color='#000000', linewidth=1)
            box.set_facecolor(color)

        ## change color and linewidth of the whiskers
        for whisker in bp['whiskers']:
            whisker.set(color='#000000', linewidth=0.8)

        ## change color and linewidth of the medians
        for median in bp['medians']:
            median.set(color='#000000', linewidth=2)

        ## change the style of fliers and their fill
        for flier in bp['fliers']:
            flier.set(marker='+', color='#999999', alpha=0.2, linewidth=0.1)

        ax.set_yscale("log")

        ax.set_xticks(pos)
        ax.set_xticklabels(nodes_list_to_plot, fontsize=fig_spec.x_axis_tick_label_fs, rotation=0)

        ax.margins(0.05)
        ax.set_axisbelow(True)
        ax.yaxis.grid(True)

        gridlines = ax.get_ygridlines()
        for line in gridlines:
            line.set_linestyle(':')
            line.set_linewidth(0.66)
            line.set_color("0.5")

    fig.text(fig_spec.subtitle_location["x"], fig_spec.subtitle_location["y"], 'nodes', ha='center',
             fontsize=fig_spec.sub_title_fs)

    plot_file = os.path.join(plot_path, "{}.pdf".format(remove_spaces(file_name)))
    save_plot_and_close(plot_file)


def plot_qualitative_information_of_modelconfigurations_using_barplot(plotting_data,
                                                                      aggregated_classification_per_mc,
                                                                      file_name="quality_30_1",
                                                                      plot_path="./plots/",
                                                                      nodes=35,
                                                                      wps=1,
                                                                      fig_spec=None,
                                                                      suptitle=None):
    ''' Plots barplots indicating qualitative information about which modelconfiguration could solve which part of
        the scenarios.

    :param plotting_data:
    :param aggregated_classification_per_mc:
    :param file_name:
    :param plot_path:
    :param nodes:
    :param wps:
    :param fig_spec:
    :param suptitle:
    :return:
    '''
    if fig_spec is None:
        fig_spec = BarPlotSpec()

    fig, ax = plt.subplots(figsize=fig_spec.fig_size)
    ax.set_title("WP={}".format(wps), fontsize=fig_spec.title_fs)
    if suptitle is not None:
        fig.suptitle(suptitle, fontsize=fig_spec.sup_title_fs, **fig_spec.suptitle_location)

    model_configurations = plotting_data.model_configurations

    labels = [get_model_configuration_description(mc) for mc in model_configurations]

    colors = ['0.5', '0.8', '1.0', '0.0']

    values = aggregated_classification_per_mc[(nodes, wps)]
    pos = [0.5 + x for x in range(len(model_configurations))]
    cumulative = [0] * (len(model_configurations))

    legend_elements = []

    for i in range(4):

        result = []
        for mc in model_configurations:
            result.append(values[mc][i])

        legend_elements.append(
            ax.bar(x=pos, height=result, bottom=cumulative, width=0.4, color=colors[i], edgecolor="k"))

        for k in range(len(cumulative)):
            cumulative[k] += result[k]

    ax.set_xticks(pos)
    ax.set_xticklabels(labels, fontsize=fig_spec.x_axis_tick_label_fs, rotation=90)
    ax.set_ylim(0, plotting_data.max_index)
    ax.set_yticklabels([0, 20, 40, 60, 80, 100], fontsize=fig_spec.y_axis_tick_label_fs)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True)

    gridlines = ax.get_ygridlines()
    for line in gridlines:
        line.set_linestyle(':')
        line.set_linewidth(0.66)
        line.set_color("0.5")

    ax.set_ylabel("scenarios [%]", fontsize=fig_spec.y_axis_label_fs)

    plt.legend(reversed(legend_elements),
               reversed(['optimal', 'feasible', 'unknown', 'infeasible']),
               loc='center left',
               bbox_to_anchor=(1, 0.5),
               prop={'size': fig_spec.legend_fs},
               borderaxespad=1)

    ax.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False,  # ticks along the top edge are off
        labelbottom=True)  # labels along the bottom edge are off

    plot_file = os.path.join(plot_path, "{}.pdf".format(remove_spaces(file_name)))
    plt.subplots_adjust(**fig_spec.subplot_adjust)
    save_plot_and_close(plot_file)


def plot_qualitative_information_across_number_of_nodes_as_line(plotting_data,
                                                                aggregated_classification,
                                                                file_name="quality_1",
                                                                plot_path="./plots/",
                                                                wps=1,
                                                                suptitle=None,
                                                                fig_spec=None):
    ''' Plots aggregates solution information over all model configurations indicating which percentage of the scenarios
        could be optimally solved, were infeasible to solve, were unknown etc.

    :param plotting_data:
    :param aggregated_classification:
    :param file_name:
    :param plot_path:
    :param wps:
    :param suptitle:
    :param fig_spec:
    :return:
    '''
    if fig_spec is None:
        fig_spec = LinePlotSpec()

    fig, ax = plt.subplots(figsize=fig_spec.fig_size)
    ax.set_title("WP={}".format(wps), fontsize=fig_spec.title_fs)
    if suptitle is not None:
        fig.suptitle(suptitle, fontsize=fig_spec.sup_title_fs, **fig_spec.suptitle_location)

    colors = {"OW": '0.00', "OS": '0.0', "F": '0.0', "U": '0.25', "I": '0.5'}
    linestyles = {"OW": '-.', "OS": ':', "F": '-', "U": '--', "I": '-'}

    y = {}
    y["OW"] = []
    y["OS"] = []
    y["F"] = []
    y["U"] = []
    y["I"] = []

    def get_label_line_quality(classifier):
        if classifier == "OS":
            return r"optimal$_{\mathrm{\mathsf{SLF}}}$"
        if classifier == "OW":
            return r"optimal$_{\mathrm{\mathsf{RLF}}}$"
        if classifier == "F":
            return "feasible"
        if classifier == "U":
            return "unknown"
        if classifier == "I":
            return "infeasible"

    x = [val for val in plotting_data.nodes]
    for nodes in x:
        opt_w, opt_s, feas, unk, inf = aggregated_classification[(nodes, wps)]
        total = float(feas + unk + inf)
        y["OW"].append(opt_w / total)
        y["OS"].append(opt_s / total)
        y["F"].append(feas / total)
        y["U"].append(unk / total)
        y["I"].append(inf / total)

    order = ["F", "OS", "OW", "U", "I"]
    for key in order:
        ax.plot(x, y[key], color=colors[key], linestyle=linestyles[key], label=get_label_line_quality(key),
                linewidth=1.6)

    ax.set_ylim(0, 1)
    ax.set_xlim(plotting_data.nodes[0], plotting_data.nodes[-1])
    ax.set_yticklabels([0, 20, 40, 60, 80, 100], fontsize=fig_spec.y_axis_tick_label_fs)
    ax.set_xlabel("nodes", fontsize=fig_spec.x_axis_label_fs)
    ax.set_ylabel("scenarios [%]", fontsize=fig_spec.y_axis_label_fs)

    minimal_node_number = plotting_data.nodes[0]
    maximal_node_number = plotting_data.nodes[-1]
    nodes_range =  maximal_node_number - minimal_node_number
    foo_labels = [x for x in range(minimal_node_number, maximal_node_number+1, nodes_range/4)]
    ax.set_xticks(foo_labels)
    ax.set_xticklabels(foo_labels, fontsize=fig_spec.x_axis_tick_label_fs)

    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(fig_spec.x_axis_tick_label_fs)
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(fig_spec.y_axis_tick_label_fs)

    ax.set_axisbelow(True)
    ax.grid(True)

    gridlines = ax.get_xgridlines() + ax.get_ygridlines()
    for line in gridlines:
        line.set_linestyle(':')
        line.set_linewidth(0.66)
        line.set_color("0.5")

    plt.legend(loc='center left',
               bbox_to_anchor=(1, 0.5),
               prop={'size': fig_spec.legend_fs},
               borderaxespad=1)
    plot_file = os.path.join(plot_path, "{}.pdf".format(remove_spaces(file_name)))
    plt.subplots_adjust(**fig_spec.subplot_adjust)
    save_plot_and_close(plot_file)


def make_ecdf_plot(pd,
                   output_path="./plots/"):
    nodes_list = [pd.nodes[0], pd.nodes[len(pd.nodes) / 2], pd.nodes[-1]]
    output_filename = "ecdf_rounds_" + "_".join(map(str, nodes_list))
    plot_ecdf_of_number_of_rounds_used_for_SLF_and_RLF(pd,
                                                       nodes_list_to_plot=nodes_list,
                                                       file_name=output_filename,
                                                       plot_path=output_path
                                                       )


def make_box_plots(pd,
                   output_path="./plots/"):
    time_until_infeasibility_or_first_solution = calculate_boxplot_runtime_values(plotting_data=pd)

    nodes_list = [pd.nodes[0], pd.nodes[len(pd.nodes) / 2], pd.nodes[-1]]

    plot_boxplot_comparison_of_different_modelconfigurations(pd,
                                                             time_until_infeasibility_or_first_solution,
                                                             "inf",
                                                             nodes_list,
                                                             file_name="box_runtime_infeasibility",
                                                             plot_path=output_path)

    plot_boxplot_comparison_of_different_modelconfigurations(pd,
                                                             time_until_infeasibility_or_first_solution,
                                                             "first",
                                                             nodes_list,
                                                             file_name="box_runtime_first_solution",
                                                             plot_path=output_path)


def make_bar_plots(pd,
                   output_path="./plots/"):
    aggregated_classification_per_mc = calculate_barplot_values_and_aggregate_quality(pd)

    selected_number_of_nodes = pd.nodes[-1]

    for index, wp in enumerate(pd.wps):
        file_name = "bar_quality_model_configuration_{}_{}".format(selected_number_of_nodes, wp)
        sup_title = None
        if index * 2 + 1 == len(pd.wps):
            #suptitle only for the middle plot
            sup_title = "Algorithm Performance"
        plot_qualitative_information_of_modelconfigurations_using_barplot(pd,
                                                                          aggregated_classification_per_mc,
                                                                          file_name=file_name,
                                                                          nodes=selected_number_of_nodes,
                                                                          wps=wp,
                                                                          suptitle=sup_title,
                                                                          plot_path=output_path)


def make_line_plots(pd,
                    output_path="./plots/"):
    aggregated_classification = calculate_lineplot_values_and_aggregate_quality(plotting_data=pd)

    for index, wp in enumerate(pd.wps):
        file_name = "line_aggregated_quality_{}".format(wp)
        sup_title = None
        if index * 2 + 1 == len(pd.wps):
            # suptitle only for the middle plot
            sup_title = "Instance Classification"
        plot_qualitative_information_across_number_of_nodes_as_line(pd,
                                                                    aggregated_classification,
                                                                    file_name=file_name,
                                                                    wps=wp,
                                                                    suptitle=sup_title,
                                                                    plot_path=output_path)


def make_all_plots_TON_TPC(pickle_name, output_path):
    print "Starting to load pickle {}".format(pickle_name)
    solution_dict = load_pickle(pickle_name)
    print "Finished reading pickle {}".format(pickle_name)

    pd = PlottingData(solution_dict)

    print("Rendering ECDF Plot(s)")
    make_ecdf_plot(pd=pd, output_path=output_path)

    print("Rendering Box Plot(s)")
    make_box_plots(pd=pd, output_path=output_path)

    print("Rendering Bar Plot(s)")
    make_bar_plots(pd=pd, output_path=output_path)

    print("Rendering Line Plot(s)")
    make_line_plots(pd=pd, output_path=output_path)





def obtain_nodes_to_optimal_solutions_per_model_config(plotting_data, model_configurations):
    result = {}
    solution_dict = plotting_data.solution_dict

    for umc in model_configurations:
        result[umc] = {}
        for wp in plotting_data.wps:
            result[umc][wp] = {}
            for node in plotting_data.nodes:
                result[umc][wp][node] = np.zeros(len(plotting_data.index))
                counter = 0
                for index in plotting_data.index:
                    extracted_solution_data = solution_dict[(node,wp,index)][umc]
                    if extracted_solution_data.classification == datamodel.ExtractedSolutionData.CLASS_OPTIMAL:
                        result[umc][wp][node][counter] = extracted_solution_data.solution
                    else:
                        result[umc][wp][node][counter] = np.NaN
                    counter += 1

    return result

def plot_new_merged_purified_all_percentiles(plotting_data,
                                             file_prefix="rounds_percentiles_",
                                             plot_path="./plots/"):

    x = list(plotting_data.nodes)
    x_min = plotting_data.nodes[0]


    umc_strong = None
    umc_relaxed = None

    for umc in plotting_data.model_configurations:
        if not umc.decision_variant and not umc.use_flow_extension:
            #only selecting
            if umc.strong_loop_freedom:
                umc_strong = umc
            else:
                umc_relaxed = umc

    model_configs = [umc_strong, umc_relaxed]

    data = obtain_nodes_to_optimal_solutions_per_model_config(plotting_data, model_configs)

    for wp in plotting_data.wps:
        import warnings
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        for node in plotting_data.nodes:
            relaxed_data = data[umc_relaxed][wp][node]
            strong_data = data[umc_strong][wp][node]
            foo = strong_data - relaxed_data
            bad_indices = np.where((foo <= -0.5))
            #remove indices for which SLF had lower rounds than RLF as this can only be due to numerical instabilities.
            #remove also all data entries for which non optimal solutions (indicated by np.NaN) were found
            bad_indices_nan = np.isnan(relaxed_data) | np.isnan(strong_data)

            for index_foo in range(np.shape(relaxed_data)[0]):
                if index_foo in bad_indices[0] or bad_indices_nan[index_foo]:
                    relaxed_data[index_foo] = np.NaN
                    strong_data[index_foo] = np.NaN

        y = {}
        y_std = {}
        y_max = {}
        y_percentiles = {}
        y_min = {}
        z = {}

        for umc in model_configs:

            strong = umc.strong_loop_freedom

            y[strong] = np.zeros(len(x))
            y_std[strong] = np.zeros(len(x))
            y_max[strong] = np.zeros(len(x))
            y_min[strong] = np.zeros(len(x))

            y_percentiles[strong] = {}
            for i in range(101):
                y_percentiles[strong][i] = np.zeros(len(x))

            z[strong] = np.zeros(len(x))


            for node in plotting_data.nodes:
                y[strong][node-x_min] = np.nanmean(data[umc][wp][node])
                y_std[strong][node-x_min] = np.nanstd(data[umc][wp][node])
                for i in y_percentiles[strong].keys():
                    y_percentiles[strong][i][node-x_min] = np.nanpercentile(data[umc][wp][node], i)

                y_min[strong][node-x_min] = np.nanmin(data[umc][wp][node])
                y_max[strong][node-x_min] = np.nanmax(data[umc][wp][node])

                count = 0.0
                for i in range(np.shape(data[umc][wp][node])[0]):
                    if not np.isnan(data[umc][wp][node][i]):
                        count += 1.0
                z[strong][node-x_min] = plotting_data.max_index-count


        options = [True, False]

        for strong in options:
            fig, ax = plt.subplots(figsize=(6,5))
            #relaxed_loop_freedom
            mean_line,  = plt.plot(x, y[strong], 'k-', linewidth=3, label="mean")
            percentiles_to_plot = [0,100]
            alphas = [0.15, 0.25, 0.15]

            plt.fill_between(x, y_min[False], y_percentiles[strong][5], alpha=1,hatch="\\", edgecolor='#000000', facecolor='#CCCCCC')
            plt.fill_between(x, y_percentiles[strong][5], y_percentiles[strong][95], alpha=1, edgecolor='#000000', facecolor='#AAAAAA')
            plt.fill_between(x, y_percentiles[strong][95], y_max[strong],  hatch="/", alpha=1, edgecolor='#000000', facecolor='#CCCCCC')


            ax.grid(True)
            import matplotlib.patches as mpatches
            a_val = 1
            legend_min = mpatches.Patch( facecolor="#CCCCCC",alpha=a_val,hatch='\\',label='min - 5%')
            legend_most = mpatches.Patch(facecolor="#AAAAAA",alpha=a_val,hatch='',label='5% - 95%')
            legend_max = mpatches.Patch( facecolor="#CCCCCC",alpha=a_val,hatch='//',label='95% - max')
            plt.ylabel("number of rounds", fontsize=14)
            plt.xlabel("number of nodes", fontsize=14)

            if strong:
                plt.title("Optimal Number of Rounds under Strong Loop Freedom\n", fontsize=14)
                ax.legend(handles = [mean_line, legend_max,legend_most,legend_min ],loc=2)
                ax.set_yscale("log", basey=2)
                plt.tight_layout()
                save_plot_and_close(plot_path + "/" + file_prefix + "_strong_loop_freedom_perc_wp_{}.pdf".format(wp))
            else:
                ax.legend(handles = [mean_line, legend_max,legend_most,legend_min ],loc=4)
                plt.title("Optimal Number of Rounds under Relaxed Loop Freedom\n", fontsize=14)
                plt.tight_layout()
                save_plot_and_close(plot_path + "/" + file_prefix + "_relaxed_loop_freedom_perc_wp_{}.pdf".format(wp))

            plt.close('all')

def make_all_plots_TON_LFRU(pickle_name, output_path):
    print "Starting to load pickle {}".format(pickle_name)
    solution_dict = load_pickle(pickle_name)
    print "Finished reading pickle {}".format(pickle_name)

    pd = PlottingData(solution_dict)

    print("Rendering Percentile Plot(s)")
    plot_new_merged_purified_all_percentiles(plotting_data=pd,
                                             plot_path=output_path)