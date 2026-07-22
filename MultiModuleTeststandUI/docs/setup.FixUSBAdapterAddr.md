# How do I fix usb adapter address
1. Find the attributes of your USB device

` udevadm info --name=/dev/ttyUSB0`

 Look for the **ATTRS{serial}** attribute and device ID. 	

` udevadm info --name=/dev/ttyUSB1 --attribute-walk | grep --max-count=1 ATTRS{serial}==`

```
### list all needed info
udevadm info --name=/dev/ttyUSB1 --attribute-walk | grep --max-count=1 ATTRS{idVendor}==
udevadm info --name=/dev/ttyUSB1 --attribute-walk | grep --max-count=1 ATTRS{serial}==
udevadm info --name=/dev/ttyUSB1 --attribute-walk | grep --max-count=1 ATTRS{idProduct}==
udevadm info --name=/dev/ttyUSB1 --attribute-walk | grep --max-count=1 SUBSYSTEM
```

1. Create a udev rule (e.g., `/etc/udev/rules.d/99-usb-serial.rules`):

```
### my config
SUBSYSTEM=="tty", ATTRS{idVendor}=="067b", ATTRS{idProduct}=="23a3", ATTRS{serial}=="EUDQb11BS12", SYMLINK+="DAQrs232_HVswitch"
```
1. Reload udev rules:

```
sudo udevadm control --reload-rules
sudo udevadm trigger
```

As a result you can check directory `/dev/DAQrs232_HVswitch` existing.
However, this device will not be shown if you use python script
```
#!/usr/bin/env python3
import pyvisa
rm = pyvisa.ResourceManager()
rm.list_resources()
>>> ('ASRL/dev/ttyUSB0::INSTR', )
```

But you can use your aliased **ASRL/dev/DAQrs232_HVswitch::INSTR** in python script
