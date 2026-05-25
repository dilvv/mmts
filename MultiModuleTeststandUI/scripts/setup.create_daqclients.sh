#!/usr/bin/env sh

SOURCE_OF_DAQCLIENTSERVICE=/usr/lib/systemd/system/daq-client.service
USER_SYSTEMD_FOLDER=${HOME}/.config/systemd/user/



function Create_user_daqclient_services() {
port=$1
outFOLDER=$USER_SYSTEMD_FOLDER
outFILE=${outFOLDER}/daq-client-port${port}.service
cp /usr/lib/systemd/system/daq-client.service $outFILE
mkdir -p $outFOLDER

## Find executable at line ExecStart
DAQCLIENT_EXEC=$(grep ExecStart $SOURCE_OF_DAQCLIENTSERVICE | cut -d'\' -f2)
DAQCLIENT_EXEC="${DAQCLIENT_EXEC#\'}"

## sed remove original ExecStart and add daq-client -p 6003
sed -i "/ExecStart/d; 7i ExecStart=$DAQCLIENT_EXEC -p ${port}" $outFILE

echo output file is $outFILE
}
function Create_daqclient_services() {
port=$1
outFILE=/usr/lib/systemd/system/daq-client-port${port}.service
cp /usr/lib/systemd/system/daq-client.service $outFILE

## Find executable at line ExecStart
DAQCLIENT_EXEC=$(grep ExecStart $SOURCE_OF_DAQCLIENTSERVICE | cut -d'\' -f2)
DAQCLIENT_EXEC="${DAQCLIENT_EXEC#\'}"

## sed remove original ExecStart and add daq-client -p 6003
sed -i "/ExecStart/d; 7i ExecStart=$DAQCLIENT_EXEC -p ${port}" $outFILE

echo output file is $outFILE
}




#Create_user_daqclient_services 6001 ## not to use 6001 because daq-client.services uses it
Create_user_daqclient_services 6002
Create_user_daqclient_services 6003
Create_user_daqclient_services 6004
Create_user_daqclient_services 6005
Create_user_daqclient_services 6006
Create_user_daqclient_services 6007
Create_user_daqclient_services 6008
Create_user_daqclient_services 6009
Create_user_daqclient_services 6010
Create_user_daqclient_services 6011
Create_user_daqclient_services 6012
Create_user_daqclient_services 6013
Create_user_daqclient_services 6014
Create_user_daqclient_services 6015
Create_user_daqclient_services 6016
Create_user_daqclient_services 6017
Create_user_daqclient_services 6018
Create_user_daqclient_services 6019
Create_user_daqclient_services 6020
Create_user_daqclient_services 6021
Create_user_daqclient_services 6022
Create_user_daqclient_services 6023
Create_user_daqclient_services 6024
Create_user_daqclient_services 6025


echo "[Usage] command 'systemctl --user restart daq-client-port6001.service'"

systemctl --user daemon-reload ## reload user daemon
#systemctl daemon-reload # no need to reload system daemon
#systemctl list-units 
