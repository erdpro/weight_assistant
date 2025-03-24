# Weight Assistant

This is a simple weight tracking script which pulls data from your Home Assistant and provides you an exponentially smoothed moving average for your weight inspired by John Walker from fourmilab.ch.

## Prequisites

* Working Home Assistant Instance
* Smart scale which sends weight data to Home Assistant
* Separate linux OS to run the code
* Telegram account

## How to setup

This script is setup to run on a local linux OS and fetch the data from your Home Assistant every time.

First you need to mount the location of your Home Assistant sqlite3 .db file to allow the code to read it:

`sudo mount -t cifs //YOUR.HASS.IP.ADDRESS/config /mnt/hass -o username=your_username,password=your_password`

To make this persistent, add this as an entry to your fstab file in /etc/fstab:

`//YOUR.HASS.IP.ADDRESS/config /mnt/hass cifs username=your_username,password=your_password 0 0`

To get the messages through telegram, you need to create a bot. The instructions for this are readily availble online. What you ultimately will need is a chat and bot ID.

Fill the relevant information in the .evn.example file provided and rename to ".env".

Next you need to trigger the code to run. This can be either done through a recurring crontab job, or have the linux server listen to traffic on a port and run a shell file when triggered:

Create a .sh file:

`sudo nano /usr/local/bin/weightassistant.sh`

Inside this .sh file insert the following (placed in the Home Assistant config folder):

`python3 /mnt/hass/python/weightassistant.py`

Make this executable:

`sudo chmod +x /usr/local/bin/weightassistant.sh`

Create a service file:

`sudo nano /etc/systemd/system/weightassistant.service`

Inside it place the following:

```
[Unit]
Description=Listener Service

[Service]
ExecStart=/usr/bin/ncat -lk -p 5000 --exec '/usr/local/bin/weightassistant.sh'
Restart=always

[Install]
WantedBy=default.target
```

**Note, this is not a secure way to activate this script as any traffic to port 5000 will trigger it. You should be aware of this.**

Now run the following:

```
sudo systemctl daemon-reload
sudo systemctl start weightassistant.service
sudo systemctl enable weightassistant.service
```

Check it's running (Active: should say "active (running)")

`sudo systemctl status weightassistant.service`

In your Home Assistant configuration.yaml file add the following and load your new config:
```
rest_command:
  weightassistant:
    url: 'http://YOUR.LINUX.IP.ADDRESS:5000'
    method: 'POST'
```

In Home Assistant add the following automation:
```
alias: Weight Assistant
description: ""
triggers:
  - trigger: state
    entity_id:
      - sensor.weight_name
conditions: []
actions:
  - action: rest_command.weightassistant
    data: {}
mode: single
```