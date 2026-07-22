sudo systemctl status firewalld ## check service is opened or not. use start and enable to make it run permanently
#sudo firewall-cmd --zone=public --add-port=5001/tcp ### temporally open
sudo firewall-cmd --zone=public --add-port=5001/tcp --permanent ### changed permanant
sudo firewall-cmd --reload
sudo firewall-cmd --list-port ### it should show 5001/tcp
