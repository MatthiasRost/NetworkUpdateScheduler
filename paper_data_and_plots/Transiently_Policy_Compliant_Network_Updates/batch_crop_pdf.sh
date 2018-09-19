#!/bin/bash
BASE="."	#if you want to call this script from another location
SOURCE=plots
FINAL=cropped_plots

echo "======================================================================================="
echo "This script was used to crop the single pdfs into an acceptable format for publication."
echo "Specifically, the bar and line plots are cropped using the same parameters to obtain equal widths (per plot) while keeping the height always the same."
echo "This script creates and deletes directories (locally in folder $BASE). You should read through the script first and make sure that you are in the correct directory."
echo "Furthermore note that some of the file paths are hard-coded."
echo "======================================================================================="

read -p "Are you sure you want to continue (y/n)?" CONT
if [ ! "$CONT" = "y" ]; then
	echo "Aborting."
	exit 1  
fi

if [ ! -d "$SOURCE" ]; then
	echo "Expecting to find the plots in directory $SOURCE. Aborting, as this directory could not be found."
	echo "Note that you may set the BASE variable in this script to whatever path you want."
	exit 1
fi

LINE_PLOTS=line_plot_cropped
BAR_PLOTS=bar_plot_cropped


rm -rf $BASE""/$LINE_PLOTS
rm -rf $BASE""/$BAR_PLOTS
rm -rf $BASE""/$FINAL

mkdir $BASE""/$LINE_PLOTS
mkdir $BASE""/$BAR_PLOTS
mkdir $BASE""/$FINAL

for f in $(find $BASE""/$SOURCE""/ -name 'line_aggregated_quality_*.pdf');
do
    filename=$(basename $f)
    filename_wo_ext=${filename%.pdf}
    dirname=$(dirname "$f")
    echo Handling $dirname""/$filename ..
    pdfcrop --margins "-52 -54 -30 -28" --bbox "0 0 432 324" $f $BASE""/$LINE_PLOTS""/l_pre_$filename
    pdfcrop --margins "-32 -54 -160 -28" --bbox "0 0 432 324" $f $BASE""/$LINE_PLOTS""/r_pre_$filename
    pdfcrop --margins "-52 -54 -160 -28" --bbox "0 0 432 324" $f $BASE""/$LINE_PLOTS""/b_pre_$filename
done

for f in $(find $BASE""/$SOURCE""/ -name 'bar_quality_model_configuration*.pdf');
do
    filename=$(basename $f)
    filename_wo_ext=${filename%.pdf}
    dirname=$(dirname "$f")
    echo Handling $dirname""/$filename ..
    pdfcrop --margins "-52 -54 -30 -28" --bbox "0 0 432 324" $f $BASE""/$BAR_PLOTS""/l_pre_$filename
    pdfcrop --margins "-32 -54 -160 -28" --bbox "0 0 432 324" $f $BASE""/$BAR_PLOTS""/r_pre_$filename
    pdfcrop --margins "-52 -54 -160 -28" --bbox "0 0 432 324" $f $BASE""/$BAR_PLOTS""/b_pre_$filename
done

for filename in ecdf_rounds_15_25_35.pdf box_runtime_first_solution.pdf box_runtime_infeasibility.pdf;
do
    pdfcrop $BASE""/$SOURCE""/$filename $BASE""/$FINAL""/$filename
done

cp $BASE""/$LINE_PLOTS""/r_pre_line_aggregated_quality_1.pdf $BASE""/$FINAL""/line_aggregated_quality_1.pdf
cp $BASE""/$LINE_PLOTS""/b_pre_line_aggregated_quality_2.pdf $BASE""/$FINAL""/line_aggregated_quality_2.pdf
cp $BASE""/$LINE_PLOTS""/b_pre_line_aggregated_quality_3.pdf $BASE""/$FINAL""/line_aggregated_quality_3.pdf
cp $BASE""/$LINE_PLOTS""/b_pre_line_aggregated_quality_4.pdf $BASE""/$FINAL""/line_aggregated_quality_4.pdf
cp $BASE""/$LINE_PLOTS""/l_pre_line_aggregated_quality_5.pdf $BASE""/$FINAL""/line_aggregated_quality_5.pdf

cp $BASE""/$BAR_PLOTS""/r_pre_bar_quality_model_configuration_35_1.pdf $BASE""/$FINAL""/bar_quality_model_configuration_35_1.pdf
cp $BASE""/$BAR_PLOTS""/b_pre_bar_quality_model_configuration_35_2.pdf $BASE""/$FINAL""/bar_quality_model_configuration_35_2.pdf
cp $BASE""/$BAR_PLOTS""/b_pre_bar_quality_model_configuration_35_3.pdf $BASE""/$FINAL""/bar_quality_model_configuration_35_3.pdf
cp $BASE""/$BAR_PLOTS""/b_pre_bar_quality_model_configuration_35_4.pdf $BASE""/$FINAL""/bar_quality_model_configuration_35_4.pdf
cp $BASE""/$BAR_PLOTS""/l_pre_bar_quality_model_configuration_35_5.pdf $BASE""/$FINAL""/bar_quality_model_configuration_35_5.pdf

rm -rf $BASE""/$LINE_PLOTS
rm -rf $BASE""/$BAR_PLOTS



