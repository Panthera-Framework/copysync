import pantheradesktop.kernel
import sys
import os
import getpass

class copySyncArguments (pantheradesktop.argsparsing.pantheraArgsParsing):
    copysync = None
    
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
        
    def setDebuggingMode(self, aaa=''):
        """
            Enable debugging mode
        """
        
        self.panthera.logging.silent = False
        
    def setPassword(self, passwd):
        """ Set remote destination password """
        
        self.panthera.password = getpass.getpass()
        
        self.panthera.logging.output('Rawwr... got your password '+str(len(self.panthera.password))+'-length password!', 'copysync')
    
    def addArgs(self):
        """ Add application command-line arguments """
    
        self.createArgument('--password', self.setPassword, '', '(Optional) Set password', required=False, action='store_false')
        self.createArgument('--debug', self.setDebuggingMode, '', 'Enable debugging mode', required=False, action='store_false')
        self.createArgument('--skip_hidden_files', self.setSkipHiddenFiles, '', 'Exclude hidden files or directories from synchronization', required=False, action='store_false')
