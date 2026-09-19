# raspicam

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt








Raspicam systemd daemon

Service: raspicam.service
File: /etc/systemd/system/raspicam.service
Project: /home/astrod/raspicam
Python: /home/astrod/raspicam/venv/bin/python

Enable at boot:
sudo systemctl enable raspicam

Start/stop/restart:
sudo systemctl start raspicam
sudo systemctl stop raspicam
sudo systemctl restart raspicam

Status:
sudo systemctl status raspicam

Logs:
journalctl -u raspicam -f

Automatically restarts on failure.