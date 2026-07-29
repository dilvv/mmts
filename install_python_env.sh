### installation using python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip3 install   flask   flask-socketio   requests   sphinx   paramiko   pyvisa   pyvisa-py   pyyaml   flask-wtf   myst-parser   flask-cors   pymeasure   psycopg psycopg2-binary
sudo apt update
sudo apt install python3-psycopg python3-psycopg-c
sudo apt update && sudo apt install firewalld

### open firewall
sudo firewall-cmd --zone=public --add-port=5001/tcp --permanent ### changed permanant
sudo firewall-cmd --reload
sudo firewall-cmd --list-port ### it should show 5001/tcp
