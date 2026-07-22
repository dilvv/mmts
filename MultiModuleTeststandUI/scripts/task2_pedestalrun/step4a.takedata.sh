#!/usr/bin/env sh

kriaIP=$1
moduleID=$2
usedPORT=${3:-6001}
jobTAG=$moduleID

if [ "$moduleID" == "" ]; then echo "[$jobTAG - JobDisabled] Empty module ID received"; exit; fi
if [ "$BASH_SCRIPT_FOLDER" == "" ]; then echo "[$jobTAG - EnvironmentFailure] Required variable BASH_SCRIPT_FOLDER not set. Load use_python_lib.sh"; exit; fi
source $BASH_SCRIPT_FOLDER/step0.functions.sh


moduleTYPE=`python3 $BASH_SCRIPT_FOLDER/decode_serialnumber_to_module_type.py $moduleID`
echo "[$jobTAG - RecognizedModuleType] the type is '$moduleTYPE'"
echo "aaaaa $moduleTYPE"

############### Need to be implemented ###############
#if [ "$moduleTYPE" == "Bare Hexaboard HD Full" ]; then
#  yamlfile=initHD-bottom.yaml
#  initpath=/home/ntucms/electronic_test_kria/HD_bottom
#fi

if [ "$moduleTYPE" == "Hexaboard HD Bottom" ]; then
  yamlfile=initHD-bottom.yaml
  initpath=/home/ntucms/electronic_test_kria/HD_bottom
fi
if [ "$moduleTYPE" == "Hexaboard HD Full" ]; then
  yamlfile=initHD_trophyV3-V3b.yaml
  initpath=/home/ntucms/electronic_test_kria/HD_full
  echo kkkkkk
fi
if [ "$moduleTYPE" == "Hexaboard HD Top" ]; then
  yamlfile=initHD-top.yaml
  initpath=/home/ntucms/electronic_test_kria/HD_Top
  echo kkkkkk
fi




if [ "$yamlfile" == "" ]; then echo "[$jobTAG - InvalidModuleType] input module ID '$moduleID' generates module type '$moduleTYPE'. No related yaml file in data taking"; exit; fi
if [ "$initpath" == "" ]; then echo "[$jobTAG - InvalidModuleType] input module ID '$moduleID' generates module type '$moduleTYPE'. No related folder in data taking"; exit; fi


echo "[$jobTAG - Running ] taking data using yamlfile $yamlfile at $initpath"
cd $initpath

data_collect_path=${initpath}/data/${moduleID}
show_sub_dirs $data_collect_path > runfolders_old # collect output folders before run

python3 pedestal_run.py -i $kriaIP -f $yamlfile -d $moduleID -I --pullerPort=$usedPORT && echo FINISHED
show_sub_dirs $data_collect_path > runfolders_new # collect output folders after run

# grab new generated folder and put the folder to DAQresults/$jobTAG/$moduleID
for new_folder  in `comm -13 $runfolders_old $runfolders_new`; do # asdf
  sh ${BASH_SCRIPT_FOLDER}/step4.1.move_result_to_DAQresults.sh $jobTAG $moduleID $new_folder # asdf
done
/bin/rm $runfolders_old $runfolders_new

#exec_at_ctrlpc "cd /home/ntucms/electronic_test_kria/HD_bottom && python3 pedestal_run.py -i $kriaIP -f initHD-bottom.yaml -d $moduleID -I && echo FINISHED"
#exec_at_ctrlpc "cd $initpath && python3 pedestal_run.py -i $kriaIP -f $yamlfile -d $moduleID -I && echo FINISHED"
### to do: Is there any method to collect output folder ?
#mv $initpath/data/$moduleID/

echo "[$jobTAG - Finished] taking data ENDED"

### errors
<<LISTED_OUTPUT_MESG
" ERROR - if nothing found in 20 second <- timeout TBD
"
LISTED_OUTPUT_MESG
