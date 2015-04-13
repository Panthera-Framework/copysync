import pantheradesktop.kernel
import sys
import os
import getpass

class copySyncArguments (pantheradesktop.argsparsing.pantheraArgsParsing):
    copysync = None
    description = 'File synchronization application. Provides a scriptable bridge between two locations with filters, plugins, shell scripts and more.'
    
    def parse(self):
        pantheradesktop.argsparsing.pantheraArgsParsing.parse(self)
        
        if len(self.opts) < 2:
            print("Invalid arguments specified. Example of usage: copysync [localpath] [remote@server:port:/path] -p password")
            sys.exit(1)
            
        self.panthera.localDirectory = os.path.abspath(self.opts[0])
        self.panthera.destinationAddress = self.opts[1]
        self.panthera.logging.output('Synhronizing local path: '+self.panthera.localDirectory, 'copysync')
        
    
    def version(self, value=''):
        """
            Example argument handler, shows application version
            
        """
    
        print(self.panthera.appName + " 0.1")
        sys.exit(0)
        
    def setSkipHiddenFiles(self, v=''):
        """
            Switch that disables synchronization for hidden files and directories
        """
        
        self.panthera.ignoreHiddenFiles = True


    def setQueuePostCommand(self, queuePostCommand):
        """
            Set command that will be sent to server after finished queued files sending
        """
        
        self.panthera.queueShellCallback = queuePostCommand
        
    def setPassword(self, passwd):
        """ Set remote destination password """
        
        self.panthera.password = getpass.getpass()
        
        self.panthera.logging.output('Rawwr... got your password '+str(len(self.panthera.password))+'-length password!', 'copysync.args')

    def readFilters(self, file):
        try:
            i = self.panthera.readFiltersFromFile(file)

            if i > 0:
                self.panthera.logging.output('Imported '+str(i)+' filters', 'copysync.args')
            else:
                self.panthera.logging.output('No any filter imported from '+str(file), 'copysync.args')

        except Exception as e:
            self.panthera.logging.output('Cannot import filters: '+str(e), 'copysync.args')

    def setBackupPath(self, path):
        """
        Set path where backup archives will be stored
        :param path:
        :return:
        """

        if not os.path.isdir(path) or not os.access(path, os.W_OK):
            print('Cannot find backup directory or backup directory is not writable')
            sys.exit(1)

        ## force load "backup" plugin if avaliable
        self.panthera.loadPlugins()

        if not 'backup' in self.app.pluginsAvailable:
            print('Cannot find "backup" plugin. Is this copysync installation missing it?')
            sys.exit(1)

        try:
            self.panthera.loadPlugin('backup')
        except Exception as e:
            print('Cannot run "backup" plugin. Details: '+str(e))
            sys.exit(1)

    def noCopy(self, value = ''):
        """
        Do not copy files, just execute command specified in a plugin or --execute when any files are modified

        :return: None
        """

        self.panthera.noCopy = True

    def setSSHKey(self, value = ''):
        """
        Specify a SSH connection key
        :param value: Input path

        :return:
        """

        if os.path.isfile(self.panthera.sshKey):
            self.panthera.sshKey = value

    def setSSHfs(self, value = ''):
        """
        Force sftp handler to use sshfs tool instead of native Paramiko library
        :param value:

        :return:
        """

        self.panthera.sshForceFuse = True

    def addArgs(self):
        """ Add application command-line arguments """
    
        self.createArgument('--execute', self.setQueuePostCommand, '', '(Optional) Execute shell command when every queue of files will be sent', required=False, action='store')
        self.createArgument('--password', self.setPassword, '', '(Optional) Set password', required=False, action='store_false')
        self.createArgument('--skip-hidden-files', self.setSkipHiddenFiles, '', '(Optional) Exclude hidden files or directories from synchronization', required=False, action='store_false')
        self.createArgument('--filters', self.readFilters, '', '(Optional) Read regex filters from file', required=False, action='store')
        self.createArgument('--backup', self.setBackupPath, '', '(Optional) Backup directory path', required=False, action='store')
        self.createArgument('--no-copy', self.noCopy, '', '(Optional) Do not copy files, just execute command specified in a plugin or --execute when any files are modified', required=False, action='store_false')
        self.createArgument('--ssh-key', self.setSSHKey, '', '(Optional) Specify a SSH authorization key, used by sftp connection handler, uses DSA algorithm (type ssh-keygen -t dsa to generate a key)', required=False, action='store')
        self.createArgument('--force-sshfs', self.setSSHfs, '', '(Optional) Force using sshfs instead of native Paramiko library to connect via sftp', required=False, action='store_false')
