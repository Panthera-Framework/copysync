#-*- encoding: utf-8 -*-
import libcopysync.watchers
import pantheradesktop.kernel
import libcopysync.handlers.ftp
import libcopysync.handlers.sftp
import libcopysync.handlers.files
import libcopysync.args
import subprocess
import sys
import time
import os
import hashlib
import pantheradesktop.tools as tools
import re
import traceback

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
    destinationParent = None
    threads = {}
    queue = {}
    queueVirtualContent = {} # alternative paths where file content is
    defaultWatcher = "fswatchdog"
    watcher = None
    localDirectory = None
    hashTable = {}
    
    # built-in options
    ignoreHiddenFiles = False
    maxFileSize = 5242880 # 5 Mbytes
    noCopy = False

    # queue
    queueLock = False
    queueShellCallback = None
    queueFilters = {}

    # handler specific
    sshKey = ""
    sshForceFuse = False
    
    
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

        # @hook app.checkDestination.handlerSelection
        tmp = self.hooking.execute('app.checkDestination.handlerSelection', tmp)
        
        try:
            self.destination = tmp.Handler(self)
            self.destination.connect(self.destinationAddress, urlparse.urlparse(self.destinationAddress))
            
        except Exception as e:
            print("Cannot connect to server: "+str(e))
            self.logging.output(traceback.format_exc(), 'copysync')
            sys.exit(1)

        # fallback
        if self.destination.status and "destinationAddress" in self.destination.status:
            self.logging.output('Falling back, set destination to '+self.destination.status['destinationAddress'], 'copysync')
            self.destinationAddress = self.destination.status['destinationAddress']

            if "destinationHandler" in self.destination.status:
                self.destinationHandler = self.destination.status['destinationHandler']

            # @hook app.checkDestination.handlerSelection.fallback
            self.destinationHandler = self.hooking.execute('app.checkDestination.handlerSelection.fallback', self.destinationHandler)
            self.checkDestination()

            
        if self.queueShellCallback:
            if not callable(getattr(self.destination, "shellExecute", None)):
                self.logging.output('Shell command will not be executed as the connection handler does not support commands execution', 'copysync')
            
        self.logging.output('Whooho, done', 'copysync')

        # @hook app.checkDestination.handlerSelection
        self.destination = self.hooking.execute('app.checkDestination.handlerSelection.done', self.destination)

        if self.noCopy:
            self.logging.output('Locking write methods as --no-copy argument was used', 'copysync')
            self.destination.sendObject = self.noCopyCallback
            self.destination.removeObject = self.noCopyCallback
            self.destination.renameObject = self.noCopyCallback
            self.destination.shellExecute = self.noCopyCallback

            # @hook app.checkDestination.handlerSelection.noCopy
            tmp = self.hooking.execute('app.checkDestination.handlerSelection.noCopy', tmp)




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

                if separator == -1:
                    continue

                regexp = line[0:separator].strip()
                action = line[separator:].strip()

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

        queueID = 0
        
        while True:
            time.sleep(0.1)
            
            if len(self.queue) > 0:
                queueID = queueID + 1
                self.hooking.execute('app.syncJob.Queue.iterate', queueID)
                
                # iterate over queue to send elements
                for item in self.queue.keys():
                    virtualPath = self.toVirtualPath(item)

                    self.hooking.execute('app.syncJob.Queue.iterate.item', {
                        'file': item,
                        'virtualPath': virtualPath,
                        'state': 'starting',
                        'queueLength': len(self.queue),
                        'result': False,
                        'retries': 0,
                        'operationType': ''
                    })
                    
                    result = False
                    fileRetries = 0
                    
                    # check hash table
                    if os.path.isfile(item):
                        hash = self.getFileHash(item)
                        
                        # skip file if it was not changed during last upload time
                        if item in self.hashTable and self.hashTable[item] == hash:
                            self.removeFromQueue(item)
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
                            try:
                                result = self.destination.sendObject(item, virtualPath)
                            except Exception:
                                pass

                            fileRetries = fileRetries + 1
                            
                            if fileRetries > 5:
                                break
                    else:
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

                    # execute actions hooked up by structural filters
                    if isinstance(self.queue[item]['hook'], list):
                        try:
                            self.executeItemAction(item)
                        except Exception as e:
                            self.logging.output('Cannot execute post-process action '+str(self.queue[item]['hook'])+' for file '+item, 'copysync')

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
                    
                self.hooking.execute('app.syncJob.Queue.iterated', queueID)
                
                # execute a shell command after queue is sent
                if self.queueShellCallback:
                    if callable(getattr(self.destination, "shellExecute", None)):
                        commandResult = ""
                        
                        try:
                            commandResult = str(self.destination.shellExecute(self.queueShellCallback))
                            self.logging.output(self.queueShellCallback+' ~ '+commandResult, 'syncjob')
                        except Exception as e:
                            self.logging.output('Cannot execute shell command "'+self.queueShellCallback+'", details: '+str(e), 'syncjob')

                        self.hooking.execute('app.syncJob.Queue.shell.executed', commandResult)

    def noCopyCallback(self, a = '', b = '', c = ''):
        """
        Empty callback that will do not allow to execute any action on destination
        :param a:
        :param b:
        :param c:
        :return:
        """

        return True
            
    def executeItemAction(self, item):
        """
        Execute action when item gets processed in queue
        :param item: path
        :return: null
        """

        if self.queue[item]['hook'][0] == 'execute':
            self.logging.output(self.queue[item]['hook'][1]+ ' ~ '+str(self.destination.shellExecute(self.queue[item]['hook'][1])), 'copysync')
        elif self.queue[item]['hook'][0] == 'local.execute':
            self.logging.output(self.queue[item]['hook'][1]+ ' $~ '+str(subprocess.getoutput(self.queue[item]['hook'][1])), 'copysync')

    
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
                if path in self.queueVirtualContent:

                    try:
                        os.unlink(self.queueVirtualContent[path])
                    except OSError:
                        pass # pass, as it will be deleted anyway with cleanup on application exit (see self.cleanupTempDir() for more informations)

                    del self.queueVirtualContent[path]

                del self.queue[path]
                self.logging.output('Removed '+path+' from queue after '+str(retries)+' write retries', 'copysync')
                return retries
            except Exception:
                retries = retries + 1
                time.sleep(self.config.getKey('queueRetryTime', 100))
                
                
        
    def appendToQueue(self, path, contents = '', forceRemove = False):
        """ 
            Safely append to queue from thread 
            Automaticaly retries with timeout on write error

            :param str path: Local file path
        """

        retries = 0
        forceContinue = False
        skipByPlugin = False
        queueHookForFile = True

        # python-like filters from plugins
        skipByPlugin, forceContinue, path = self.hooking.execute('app.syncJob.Queue.append.before', [skipByPlugin, forceContinue, path])

        if self.queueLock:
            return False

        if contents:
            tmp = open(self.tmpDir+"/"+hashlib.md5(path).hexdigest(), "w")
            tmp.write(contents)
            tmp.close()

        if skipByPlugin:
            return 0

        if self.queueFilters:
            for regex in self.queueFilters:
                isRegex = False
                argumentToReplace = False

                # exact path match
                if regex[0:2] == '==' and path == regex[2:]:
                    result = True
                    argumentToReplace = regex[2:]
                # exact filename (basename with extension) match
                elif regex[0:1] == '=' and os.path.basename(path) == regex[1:]:
                    result = True
                    argumentToReplace = regex[1:]
                # regex match
                else:
                    isRegex = True
                    result = re.findall(regex, path)

                if not result:
                    continue


                action = self.queueFilters[regex]

                if isRegex:
                    for i in range(0, len(result)):
                        action = action.replace('$'+str(i+1), result[i])

                if argumentToReplace:
                    action = action.replace('$0', str(argumentToReplace))

                action = action.replace('$file', os.path.basename(path))
                action = action.replace('$path', path)
                action = action.split(':')

                if len(action) < 1:
                    continue

                action[0] = action[0].replace('= ', '')

                if action[0] == 'skip':
                    self.hooking.execute('app.syncJob.Queue.append', {
                        'file': path,
                        'virtualPath': self.toVirtualPath(path),
                        'status': 'skipped',
                        'reason': 'skipped_by_filter'
                    })
                    return 0

                queueHookForFile = action



        # skipping hidden files
        if self.ignoreHiddenFiles and "/." in self.toVirtualPath(path) and not forceContinue:
            self.hooking.execute('app.syncJob.Queue.append', {
                'file': path,
                'virtualPath': self.toVirtualPath(path),
                'status': 'skipped',
                'reason': 'hidden_files_are_ignored'
            })
            return 0
        
        # filesize limit
        if os.path.isfile(path) and self.maxFileSize > 0 and os.path.getsize(path) > self.maxFileSize and not forceContinue:
            self.hooking.execute('app.syncJob.Queue.append', {
                'file': path,
                'virtualPath': self.toVirtualPath(path),
                'status': 'skipped',
                'reason': 'file_size_too_big'
            })
            return 0
        
        while True:
            if path in self.queue:
                return 0
            
            try:
                if contents:
                    self.queueVirtualContent[path] = self.tmpDir+"/"+hashlib.md5(path).hexdigest()

                self.queue[path] = {
                    'hook': queueHookForFile,
                    'remove': forceRemove
                }

                self.hooking.execute('app.syncJob.Queue.append.after', {
                    'file': path,
                    'virtualPath': self.toVirtualPath(path),
                    'status': 'success'
                })

                self.logging.output('Added '+path+' to queue after '+str(retries)+' write retries', 'copysync')
                return retries

            except Exception:
                retries = retries + 1
                time.sleep(self.config.getKey('queueRetryTime', 1))

    def cleanupTempDir(self):
        """
        Remove a temporary directory
        :return:
        """

        os.system("rm -rf /tmp/.copysync-"+str(os.getpid()))
    
    def mainLoop(self, a=''):
        """ Application's main function """

        ## temporary directory
        self.tmpDir = '/tmp/.copysync-'+str(os.getpid())

        if not os.path.isdir(self.tmpDir):
            os.mkdir(self.tmpDir)

        self.hooking.addOption('app.pa_exit', self.cleanupTempDir)


        ## settings
        self.logging.dateFormat = '%H:%m:%S %d.%m.%Y'
        
        self.maxFileSize = tools.human2bytes(self.config.getKey('maxFileSize', '5M'))
        self.logging.output('Max file size limit set to '+str(self.config.getKey('maxFileSize', '5M'))+' ('+str(self.maxFileSize)+' bytes)', 'copysync')
        
        self.checkDestination()
        self.threads['syncthread'] = tools.createThread(self.syncJob)
        self.filesystemWatchJob()
        