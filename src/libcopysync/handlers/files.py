import os
import sys
import shutil
import subprocess

class Handler:
    app = None
    path = None
    status = {}
    
    def __init__(self, app):
        """ Constructor """
        
        self.app = app
        
        
    def connect(self, url, data):
        """
        Perform a argument validation, check if paths are writable

        :param url: raw url
        :param data: urlparsed url
        :return: None
        """

        self.app.logging.output('Initializing files handler for url '+url, 'files')

        if not "path" in data and not url.startswith('/'):
            print("Not a valid filesystem path")
            sys.exit(1)

        if not url.startswith('/'):
            url = data.path
            
        if not os.access(url, os.W_OK):
            print("Selected path is not writable")
            sys.exit(1)

        self.path = url


    def sendObject(self, local, remote):
        """
        Copy a file or directory

        :param local: Local path
        :param remote: Remote path
        :return: Bool
        """

        remoteAbs = os.path.abspath(self.path+remote)
        self.app.logging.output(local+ ' -> '+remoteAbs, 'files')

        if os.path.isfile(local):
            # try to make directories recursively
            if not os.path.isdir(os.path.dirname(remoteAbs)):
                try:
                    os.makedirs(os.path.dirname(remoteAbs))
                except Exception as e:
                    self.app.logging.output('Cannot do mkdir -p '+os.path.dirname(remoteAbs)+', details: '+str(e), 'files')

            # try to copy a file
            try:
                shutil.copy2(local, remoteAbs)
            except Exception as e:
                self.app.logging.output('Cannot do copy -p '+local+' '+remoteAbs+', details: '+str(e), 'files')

        # if input path is a directory then try to create directories recursively
        if os.path.isdir(local):
            if not os.path.isdir(remoteAbs):
                try:
                    os.makedirs(remoteAbs)
                except Exception as e:
                    self.app.logging.output('Cannot do mkdir -p '+remoteAbs+', details: '+str(e), 'files')

        return True


    def removeObject(self, local, remote):
        """ Remove a file or directoy from remote destination """

        remoteAbs = os.path.abspath(self.path+remote)
        self.app.logging.output(local+ ' -/> '+remoteAbs, 'files')

        try:
            if os.path.isfile(remoteAbs):
                os.remove(remoteAbs)
            elif os.path.isdir(remoteAbs):
                os.rmdir(remoteAbs)
        except Exception as e:
            self.app.logging.output('Cannot delete remove file "'+remote+'", details: '+str(e), 'sftp')

        return True

    def shellExecute(self, command):
        """
            Execute a shell command

            :param command: command string
            :return: result list of every executed command
        """

        os.chdir(self.path)
        return subprocess.check_output(command, shell=True)