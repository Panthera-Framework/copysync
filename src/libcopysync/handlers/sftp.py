import pysftp
import os
import socket
import time
import traceback
import sys
import pexpect

class Handler:
    connection = None
    hostname = None
    username = None
    password = None
    port = 22
    app = None
    path = None
    sshfs = None
    status = {}

    def __init__(self, app):
        """ Constructor """
        
        self.app = app
        self.port = app.config.getKey('defaultSSHPort', 22)
    
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

        ## force use SSHfs tool instead of Paramiko
        if self.app.sshForceFuse:
            self.useSSHfs()
            return


        ## fallback to files handler on paramiko compatibility failure (will connect via sshfs using files handler)
        try:
            self.reconnect(useKey=(self.app.sshKey is not ""))

        except Exception as e:
            if "Incompatible ssh peer" in e.message:
                self.app.logging.output('Falling back to sshfs', 'sftp')
                self.useSSHfs()
            else:
                self.app.logging.output('Cannot connect to server, details: ' + str(e.message), 'sftp')
                print('Cannot connect to server, details: ' + str(e.message))
                traceback.print_exc()
                sys.exit(1)

    def useSSHfs(self):
        """
        Use SSHFS instead of Paramiko library

        :return:
        """

        self.app.hooking.addOption('app.pa_exit', self.cleanupSSHFS)
        os.mkdir("/tmp/copysync-sshfs-"+str(os.getpid()))
        command = "sshfs "+self.username+"@"+self.hostname+":"+self.path+" /tmp/copysync-sshfs-"+str(os.getpid())+" -p "+str(self.port)+" -o auto_unmount"

        if self.password:
            command += ",password_stdin"

        self.app.logging.output(command, 'sftp')

        self.sshfs = pexpect.spawn(command)

        if self.password:
            self.sshfs.expect("")
            time.sleep(1)
            self.sshfs.sendline(self.password)

        ## response
        response = self.sshfs.readline()
        self.app.logging.output('SSHfs output: ' +response.rstrip(), 'sftp')

        if "read:" in response:
            self.app.logging.output('Error connecting using SSHfs handler', 'sftp')
            sys.exit(1)

        self.status = {
            'destinationAddress': "/tmp/copysync-sshfs-"+str(os.getpid()),
            'destinationHandler': 'files'
        }



    def cleanupSSHFS(self, opts = ''):
        """
        Clean up after sshfs fallback session
        :param opts:
        :return:
        """

        os.system("fusermount -zu /tmp/copysync-sshfs-"+str(os.getpid()))
        os.system("rm /tmp/copysync-sshfs-"+str(os.getpid())+" -rf")

    def reconnect(self, useKey = False):
        """
        Make a reconnection using same connection parameters as previous
        :return: None
        """

        privateKey = None
        privateKeyPass = None

        # use a key authentication instead of password
        if useKey:
            # use a private key specified from commandline
            if self.app.sshKey:
                privateKey = self.app.sshKey
            else:
                privateKey = os.path.expanduser('~/.ssh/id_dsa')

            privateKeyPass = self.password
            self.password = None
            self.app.logging.output('Using private key from "' + privateKey + '"', 'sftp')


        try:
            self.connection = pysftp.Connection(self.hostname, username=self.username, password=self.password, port=self.port, private_key=privateKey, private_key_pass=privateKeyPass)
            self.connection.timeout = self.app.config.getKey('connectionTimeout', 5)
        except Exception as e:
            if ("Bad authentication type" in e.message or "not a valid DSA private key file" in e.message) and not useKey:
                self.app.logging.output('Got "Bad authentication type", trying with key authentication', 'sftp')
                self.reconnect(useKey = True)
            else:
                raise e

    def __reconnectionProxy(self, method, *args):
        """
        A proxy method that is reconnecting to server when connection gets broken
        :param local:
        :param remote:
        :return:
        """

        obj = eval('self.'+method)

        try:
            code = obj(*args)
        except socket.error as e:
            time.sleep(1)
            self.app.logging.output('Reconnecting to remote host', 'sftp')

            try:
                self.reconnect()
            except Exception as e:
                pass

            return obj(*args)
        except Exception as e:
            self.app.logging.output('Got unexpected exception '+str(e)+' for method '+str(method)+str(args)+', '+str(traceback.format_exc()), 'sftp')
            return True

        return code


    def sendObject(self, local, remote):
        """
        :param local: Local path
        :param remote: Remote path
        :return: int exit code
        """

        return self.__reconnectionProxy('_sendObject', local, remote)

    def _sendObject(self, local, remote):
        """ Copy a file or directory """

        remoteAbs = os.path.abspath(self.path+remote)
        self.app.logging.output(local+ ' -> '+remoteAbs, 'sftp')
        
        if os.path.isfile(local):
            try:
                self.connection.put(local, remoteAbs, preserve_mtime=self.app.config.getKey('sftp.preserveModificationTime', False))
            except OSError as e:
                self.app.logging.output('sftp copy failed on '+remote+', details: '+str(e), 'sftp')
        else:
            
            try:
                self.connection.makedirs(remoteAbs)
            except OSError as e:
                self.app.logging.output('mkdir failed on '+remote+', details: '+str(e), 'sftp')
        
        return True


    def removeObject(self, local, remote):
        """ Remove a file or directoy from remote destination """

        """
        :param local: Local path
        :param remote: Remote path
        :return: int exit code
        """

        return self.__reconnectionProxy('_removeObject', local, remote)
    
    def _removeObject(self, local, remote):
        """ Remove a file or directoy from remote destination """
        
        remoteAbs = os.path.abspath(self.path+remote)

        try:
            if os.path.isfile(local):
                self.connection.remove(remoteAbs)
            else:
                self.connection.rmdir(remoteAbs)

            self.app.logging.output('rm '+remoteAbs, 'sftp')
        except Exception as e:
            #self.app.logging.output('Cannot remove file "'+remoteAbs+'", details: '+str(e), 'sftp')
            self.app.logging.output('shell/rm '+remoteAbs, 'sftp')
            self.connection.execute('rm '+remoteAbs)

        return True
    
    def shellExecute(self, command):
        """
            Execute a shell command
            
            :param command: command string
            :return: result list of every executed command
        """

        self.connection.chdir(self.path)
        return self.connection.execute(command)