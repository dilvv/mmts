#!/usr/bin/env sh
folder=/Users/noises/Desktop/fake_data/data/320XHB03PP00006/pedestal_run/


jobTAG=${1:-pedestaljob1}
hexaboardID=${2:-320THEboardID}

if [ "$hexaboardID" == "" ]; then echo "[$jobTAG - JobDisabled] Empty module ID received"; exit; fi
if [ "$BASH_SCRIPT_FOLDER" == "" ]; then echo "[$jobTAG - EnvironmentFailure] Required variable BASH_SCRIPT_FOLDER not set. Load use_python_lib.sh"; exit; fi
source $BASH_SCRIPT_FOLDER/step0.functions.sh


show_sub_dirs $folder > a
mkdir ${folder}/aaa

show_sub_dirs $folder > b
for new_folder  in `comm -13 a b`; do
  sh step42.move.sh $jobTAG $hexaboardID $new_folder
done
rmdir ${folder}/aaa
rm a b
