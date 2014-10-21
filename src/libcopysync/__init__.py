#-*- encoding: utf-8 -*-
import libcopysync.watchers
import pantheradesktop.kernel
import libcopysync.handlers.ftp
import libcopysync.handlers.sftp
import libcopysync.handlers.files
import libcopysync.args
import sys
import time
import os
import hashlib
import pantheradesktop.tools as tools
import re

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse



def runInstance(a=0):
    """ Run instance of application """
    
    kernel = copysyncMainClass()
    kernel.appName = 'copysync'
    kernel.coreClasses['gui'] = False
    kernel.coreClasses['db'] = False
    kernel.coreClasses['argsparsing'] = libcopysync.args.copySyncArguments
    kernel.initialize(quiet=True)
    kernel.hooking.addOption('app.mainloop', kernel.mainLoop)
    kernel.main()
    
    
    
class copysyncMainClass (pantheradesktop.kernel.pantheraDesktopApplication, pantheradesktop.kernel.Singleton):
    """ Main class """
    
    password = None
    destinationAddress = None
    destinationHandler = 'files'
    destination = None
    threads = {};
    queue = {};
    defaultWatcher = "fswatchdog"
    watcher = None
    localDirectory = None
    hashTable = {}
    
    # built-in options
    ignoreHiddenFiles = False
    maxFileSize = 5242880 # 5 Mbytes
    queueShellCallback = None
    
    
    def checkDestination(self):
        """ Connect to destination """
        
        if self.destinationAddress[0:7] == 'sftp://':
            self.destinationHandler = 'sftp'
            tmp = libcopysync.handlers.sftp
            
        if self.destinationAddress[0:6] == 'ftp://':
            self.destinationHandler = 'ftp'
            tmp = libcopysync.handlers.ftp
            
        if self.destinationHandler == 'files':
            tmp = libcopysync.handlers.files
        
        # logging
        self.logging.output("Connecting to "+self.destinationAddress+" via "+self.destinationHandler+" handler", "copysync")
        
        try:
            self.destination = tmp.Handler(self)
            self.destination.connect(self.destinationAddress, urlparse.urlparse(self.destinationAddress))
            
        except Exception as e:
            print("Cannot connect to server: "+str(e))
            sys.exit(1)
            
        if self.queueShellCallback:
            if not callable(getattr(self.destination, "shellExecute", None)):
                self.logging.output('Shell command will not be executed as the connection handler does not support commands execution', 'copysync')
            
        self.logging.output('Whooho, done', 'copysync')

    def readFiltersFromFile(self, path):
        """
        Read queue filters from a file

        Example file format:
        tmp = skip
        /\/tmp\/(.*).test/i = execute:echo "test" > ~/.aaa

        :param path: Path to file
        :return:
        """

        if os.path.isfile(path) and os.access(path, os.R_OK):
            file = open(path, "r")

            # queueFilters
            i = 0

            for line in file.readlines():
                separator = line.find(' = ')

                if separator === -1:
                    continue

                regexp = line[0:separator].trim()
                action = line[separator:].trim()

                self.queueFilters[regexp] = action
                i = i + 1

            return i

        return 0



        
    def getFileHash(self, path, blockSize=2**20):
        """ Get file hash, supports big files 
        :rtype : str
        """
        
        md5 = hashlib.md5()
        
        if not os.path.isfile(path) or not os.access(path, os.R_OK):
            return ""

        try:
            f = open(path, "r")

            while True:
                data = f.read(blockSize)

                if not data:
                    break

                md5.update(data)
        except Exception:
            return ""
        
        
        return md5.digest()
        
        
    def syncJob(self, thread):
        """ This job is taking care of queued files to copy to remote server """
        
        while True:
            time.sleep(0.1)
            
            if len(self.queue) > 0:
                self.hooking.execute('app.syncJob.Queue.iterate', self.queue)
                
                # iterate over queue to send elements
                for item in self.queue.keys():
                    virtualPath = self.toVirtualPath(item)

                    #print("STARTING: "+item)
                    
                    self.hooking.execute('app.syncJob.Queue.iterate.item', {
                        'file': item,
                        'virtualPath': virtualPath,
                        'state': 'starting',
                        'queueLength': len(self.queue),
                        'result': False,
                        'retries': 0
                    })
                    
                    result = False
                    fileRetries = 0
                    
                    # check hash table
                    if os.path.isfile(item):
                        hash = self.getFileHash(item)
                        
                        # skip file if it was not changed during last upload time
                        if item in self.hashTable and self.hashTable[item] == hash:
                            self.removeFromQueue(item)
                            #print("REMOVED BY HASH "+str(item))
                            continue
                        
                        self.hashTable[item] = hash
                    
                    
                    # if file or directory exists
                    if os.path.isfile(item) or os.path.isdir(item):
                        operationType = "add"
                        
                        try:
                            result = self.destination.sendObject(item, virtualPath)
                        except Exception:
                            pass
                        
                        while not result:
                            result = self.destination.sendObject(item, virtualPath)
                            fileRetries = fileRetries + 1
                            
                            if fileRetries > 5:
                                break
                    else:
                        #print("REMOVE "+str(item))
                        operationType = "remove"
                        
                        # if file or directory does not exists anymore
                        try:
                            result = self.destination.removeObject(item, virtualPath)
                        except Exception:
                            pass
                        
                        while not result:
                            result = self.destination.removeObject(item, virtualPath)
                            fileRetries = fileRetries + 1
                            
                            if fileRetries > 5:
                                break
                        
                    print(operationType+" "+item)
                        
                    # remove item from queue afery copy operation
                    self.removeFromQueue(item)
                    self.hooking.execute('app.syncJob.Queue.iterate.item', {
                        'file': item, 
                        'virtualPath': virtualPath, 
                        'state': 'finished', 
                        'queueLength': len(self.queue), 
                        'result': result, 
                        'retries': fileRetries,
                        'operationType': operationType
                    })
                    
                self.hooking.execute('app.syncJob.Queue.iterated', self.queue)
                
                # execute a shell command after queue is sent
                if self.queueShellCallback:
                    if callable(getattr(self.destination, "shellExecute", None)):
                        commandResult = ""
                        
                        try:
                            commandResult = str(self.destination.shellExecute(self.queueShellCallback))
                            self.logging.output(self.queueShellCallback+' ~ '+commandResult, 'syncjob')
                        except Exception:
                            self.logging.output('Cannot execute shell command "'+self.queueShellCallback, 'syncjob')

                        self.hooking.execute('app.syncJob.Queue.shell.executed', commandResult)
                
            
            
    
    def toVirtualPath(self, path):
        """ Convert local or destination path to virtual path """
        
        if path[0:len(self.localDirectory)] == self.localDirectory:
            path = path[len(self.localDirectory):]
            
        if path[0:len(self.destination.path)] == self.destination.path:
            path = path[len(self.destination.path):]
            
        return path
    
    
       
    def filesystemWatchJob(self):
        """ Run a filesystem watching job """
        
        self.logging.output('Initializing watcher '+self.defaultWatcher, 'copysync')
        self.watcher = eval('libcopysync.watchers.'+self.defaultWatcher+'.Watcher()')
        self.watcher.directory = self.localDirectory
        self.watcher.startWatching(self)
        
        
        
    def removeFromQueue(self, path):
        """
            Safely remove item from queue
        """
        
        retries = 0
        
        while True:
            if not path in self.queue:
                return 0
            
            try:
                del self.queue[path]
                self.logging.output('Removed '+path+' from queue after '+str(retries)+' write retries', 'copysync')
                return retries
            except Exception:
                retries = retries + 1
                time.sleep(self.config.getKey('queueRetryTime', 100))
                
                
        
    def appendToQueue(self, path):
        """ 
            Safely append to queue from thread 
            Automaticaly retries with timeout on write error
        """
        
        retries = 0
        forceContinue = False
        skipByPlugin = False

        # python-like filters from plugins
        skipByPlugin, forceContinue, path = self.hooking.execute('app.syncJob.Queue.append.before', [skipByPlugin, forceContinue, path])

        if skipByPlugin:
            return 0

        #self.queueFilters = {
        #    '([A-Za-z0-9]+)': 'skip'
        #}

        if self.queueFilters:
            for regex in self.queueFilters:
                regexResult = re.findall(regex, path)
                action = self.queueFilters[regex]

                if not regexResult:
                    continue

                action = action.replace('$1', regexResult[0])
                action = action.split(':')

                if len(action) < 1:
                    continue

                if action[0] == 'skip':
                    return 0



        # skipping hidden files
        if self.ignoreHiddenFiles and "/." in self.toVirtualPath(path) and not forceContinue:
            self.hooking.execute('app.syncJob.Queue.append', {
                'status': 'skipped',
                'reason': 'hidden_files_are_ignored'
            })
            return 0
        
        # filesize limit
        if os.path.isfile(path) and self.maxFileSize > 0 and os.path.getsize(path) > self.maxFileSize and not forceContinue:
            self.hooking.execute('app.syncJob.Queue.append', {
                'status': 'skipped',
                'reason': 'file_size_too_big'
            })
            return 0
        
        while True:
            if path in self.queue:
                return 0
            
            try:
                self.queue[path] = True
                self.logging.output('Added '+path+' to queue after '+str(retries)+' write retries', 'copysync')
                return retries

            except Exception:
                retries = retries + 1
                time.sleep(self.config.getKey('queueRetryTime', 100))

                
    
    def mainLoop(self, a=''):
        """ Application's main function """
        
        self.maxFileSize = tools.human2bytes(self.config.getKey('maxFileSize', '5M'))
        self.logging.output('Max file size limit set to '+str(self.config.getKey('maxFileSize', '5M'))+' ('+str(self.maxFileSize)+' bytes)', 'copysync')
        
        self.checkDestination()
        self.threads['syncthread'] = pantheradesktop.kernel.createThread(self.syncJob)
        self.filesystemWatchJob()
        