#!/usr/bin/env sh

jobTAG=${1-pedestaljob1}
moduleID=${2}
inFOLDER=`realpath $3`

if [ ! -d "$inFOLDER" ]; then the_exit "[$jobTAG - InvalidInputFolder] '$inFOLDER' does not exist... abort"; fi
if [ "$BASH_SCRIPT_FOLDER" == "" ]; then echo "[$jobTAG - EnvironmentFailure] Required variable BASH_SCRIPT_FOLDER not set. Load use_python_lib.sh"; exit; fi
source $BASH_SCRIPT_FOLDER/step0.functions.sh


the_folder=${BASH_SCRIPT_FOLDER}/../DAQresults/$jobTAG/
mkdir -p $the_folder
out_destnation=${the_folder}/${moduleID}
#cp -r $inFOLDER $out_destnation
ln -s $inFOLDER $out_destnation
echo $inFOLDER > $out_destnation/source.txt

