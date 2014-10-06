copysync
========

Copysync is monitoring directories for changes and copying files from local to remote destination on every file change

## Installing

```bash
pip install watchdog
pip install pysftp
cd /tmp
git clone https://github.com/Panthera-Framework/Panthera-Desktop.git
cd Panthera-Framework
sudo python ./setup.py install
cd /tmp
git clone https://github.com/Panthera-Framework/copysync.git
cd copysync
sudo python ./setup.py install
```

## Example of usage

```bash
copysync /path/to/local/workspace sftp://user@server.org:22/var/www/ --password
```
