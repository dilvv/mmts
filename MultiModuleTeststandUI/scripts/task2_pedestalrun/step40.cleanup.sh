#!/usr/bin/env sh

if [ "$BASH_SCRIPT_FOLDER" == "" ]; then echo "[$jobTAG - EnvironmentFailure] Required variable BASH_SCRIPT_FOLDER not set. Load use_python_lib.sh"; exit; fi
source $BASH_SCRIPT_FOLDER/step0.functions.sh


the_folder=${BASH_SCRIPT_FOLDER}/../DAQresults/
/bin/rm -rf $the_folder
