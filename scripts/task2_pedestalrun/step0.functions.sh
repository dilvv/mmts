#!/usr/bin/env sh
function exec_at_kria() {
  cmd=$1
#ssh -i /Users/noises/.ssh/hgcalMMTS root@192.168.50.180 $cmd
### at 913
#ssh -i /home/ntucms/.ssh/HGCtrler_key_kria root@192.168.50.180 $cmd
### B2 HD full
echo "[exec_at_kria] send commands to 2 kria"
echo "[exec_at_kria] root@192.168.50.153"
ssh -i /home/ntucms/.ssh/HGCtrler_key_kria root@192.168.50.153 $cmd
echo ""
echo "[exec_at_kria] root@192.168.50.152"
ssh -i /home/ntucms/.ssh/HGCtrler_key_kria root@192.168.50.152 $cmd
}
function exec_at_kria_IP() {
  kriaIPaddr=$1
  cmd=$2
ssh -i /home/ntucms/.ssh/HGCtrler_key_kria root@${kriaIPaddr} $cmd
}
function exec_at_ctrlpc() {
  cmd=$1
#ssh -i /Users/noises/.ssh/hgcalMMTS ntucms@192.168.50.144 $cmd
eval $cmd
}
function the_exit() { echo "ERROR - "$1; exit 1; }

function show_sub_dirs() {
  # use res=`show_sub_dirs $folder` to get result
  inFOLDER=$1
  if [ ! -d "$inFOLDER" ];then return; fi # if folder not found, show nothing
  abs_in_folder=`realpath $inFOLDER`
  for a in `ls -d ${abs_in_folder}/*`; do echo $a;done # if folder found, show sub dirs
}
##### usage ##########
# show_sub_dirs $folder > a
# mkdir ${folder}/aaa
# show_sub_dirs $folder > b
# for a  in `comm -13 a b`; do echo hHHHHH $a;done
# rmdir ${folder}/aaa
# rm a b





#exec_at_ctrlpc "echo hiii jjj"
