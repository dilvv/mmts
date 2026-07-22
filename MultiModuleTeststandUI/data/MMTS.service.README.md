# Put this reopsitory as a system service

```
chmod +x ../app.py
### edit path in `data/MMTS.service`
cd .. && python3 data/MMTS.service.createscript.py
sudo cp data/MMTS.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start MMTS.service ### activate service
#sudo systemctl stop  MMTS.service ### stop service
#journalctl -u MMTS.service  ### check error messages
```
