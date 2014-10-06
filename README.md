copysync
========

Copysync is monitoring directories for changes and copying files from local to remote destination on every file change

**Programmers using GIT/SVN please note:** If you switch branch on your source (eg. localhost) computer it will copy all branch files to destination. If you don't want to switch branch on remote destination eg. testing www server please kill copysync first

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
