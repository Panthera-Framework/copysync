import pysftp
import os

class Handler:
    connection = None
    hostname = None
    username = None
    password = None
    port = 22
    app = None
    path = None
    
    def __init__(self, app):
        """ Constructor """
        
        self.app = app
    
    def connect(self, url, data):
        """
            Connect to remote server using SFTP connection protocol
        """
        
        # user:passwd@host:port
        try:
            atSplit = data.netloc.split('@')
            user = atSplit[0].split(':')
            host = atSplit[1].split(':')
            
            self.username = user[0]
            self.hostname = host[0]
            
            if len(host) == 2:
                self.port = int(host[1])
                
            if len(user) == 2:
                self.password = user[1]
        except Exception:
            print("Invalid remote sftp path specified syntax: sftp://user:pass@host:port/remote/path, example: sftp://john:test123@localhost:22/tmp/mydir")
            sys.exit(1)
            
        if self.app.password:
            self.password = self.app.password
            
        # destination path
        self.path = data.path
            
        self.connection = pysftp.Connection(self.hostname, username=self.username, password=self.password, port=self.port)
        
    def sendObject(self, local, remote):
        """ Copy a file or directory """
        
        remoteAbs = os.path.abspath(self.path+remote)
        
        if os.path.isfile(local):
            try:
                self.connection.put(local, remoteAbs, preserve_mtime=True)
            except Exception as e:
                self.app.logging.output('sftp copy failed on '+remote+', details: '+str(e))
        else:
            
            try:
                self.connection.makedirs(remoteAbs)
            except OSError as e:
                self.app.logging.output('mkdir failed on '+remote+', details: '+str(e))
        
        return True
