#-*- encoding: utf-8 -*-
import subprocess
import os

"""
Plugin that verifies if file was correctly uploaded

:author: Damian Kęska
"""

class checksumPlugin:
    avaliableCommands = {
        'md5sum': False,
        'sha1sum': False,
        'sha224sum': False,
        'sha384sum': False,
        'sha512sum': False
    }

    summingFunction = 'md5sum'
    enabled = False

    def __init__(self, app):
        """
        Constructor of a plugin
        :param app: Panthera Framework based application main class object
        :author: Damian Kęska
        :return:
        """

        self.kernel = app

        # could be also for example "sha256sum" or "sha1sum", "sha512sum" etc.
        self.kernel.config.getKey('checksum/defaultShellCommand', 'md5sum')

        # add a custom argsparsing argument
        self.kernel.hooking.addOption('app.argsparsing.__init__.after', self.addArgsParsingArguments, priority=97)





    def addArgsParsingArguments(self, argsParsing):
        """
        Add arguments to argsparsing

        :param argsParsing: Object
        :author: Damian Kęska
        :return:
        """

        argsParsing.createArgument('--verify-checksum', self.__pluginInit__, 'Verify checksum after file upload', action='store_true', required=False)



    def checkCommands(self, commands, remote = False):
        """
        Verify if commands exists

        :param string command: Command to check
        :param bool remote: Check on destination?
        :author: Damian Kęska
        :return:
        """


        ## Create a Unix shell command
        commandString = ''

        for command in commands:
            commandString = commandString + 'whereis ' + command + ' && '

        commandString = commandString.rstrip('&& ').strip()


        ## Execute the command
        if remote:
            # at first check if connection supports executing shell commands
            if not callable(getattr(self.kernel.destination, "shellExecute", None)):
                return False

            response = self.kernel.destination.shellExecute(commandString)
        else:
            response = subprocess.check_output(commandString, shell = True).split('\n')

        if not response:
            return dict()

        ## Parse the response
        foundCommands = dict()

        for line in response:
            exp = line.split(':')

            if not len(exp) or not exp[0]:
                continue

            if len(exp) > 1 and exp[1].strip():
                foundCommands[exp[0]] = True
                continue

            foundCommands[exp[0]] = False

        return foundCommands



    def verifyAvaliableCommands(self):
        """
        This function is verifying what hasing functions are avaliable locally

        :author: Damian Kęska
        :return:
        """

        commandsList = list()

        for commandName, value in self.avaliableCommands.copy().iteritems():
            commandsList.append(commandName)

        result = self.checkCommands(commandsList, remote = False)

        if result:
            self.avaliableCommands = result

        self.kernel.logging.output('Algorithms available locally: ' + str(result), 'plugins.checksum')
        return True




    def checkRemoteHost(self, destination):
        """
        This function is verifying what hasing functions are avaliable remotely
        :return:
        """

        ## Convert to List()
        commandsList = list()

        for commandName, value in self.avaliableCommands.copy().iteritems():
            commandsList.append(commandName)

        result = self.checkCommands(commandsList, remote = True)

        ## Update list, set command availability to True only when both lists have it as True, and to False if at least of it is false
        for commandName, value in result.iteritems():
            if value and self.avaliableCommands[commandName]:
                self.avaliableCommands[commandName] = True
                self.summingFunction = commandName
                continue

            self.avaliableCommands[commandName] = False

        self.kernel.logging.output('Algorithms available on remote: ' + str(result), 'plugins.checksum')
        return destination



    def verifySum(self, path, remote):
        """
        Calculate a file checksum via shell command

        :param path: Path
        :param remote: Execute on remote or on local machine?
        :return: boolean
        """

        result = ''

        try:
            if remote:
                result = self.kernel.destination.shellExecute(self.summingFunction + ' ./"' + path + '"')[0]
            else:
                result = subprocess.check_output(self.summingFunction + ' "' + self.kernel.localDirectory + '/' +path + '"', shell = True, stderr=open('/dev/null', 'r'))
        except subprocess.CalledProcessError:
            pass

        if not result or self.summingFunction + ':' in result:
            return ''

        exp = result.split(' ')
        return exp[0]



    def compareFile(self, path):
        """
        Compare local and remote file

        :param path:
        :return: boolean
        """

        ## Don't compare directories
        if os.path.isdir(self.kernel.localDirectory + '/' +path):
            return True

        remote = self.verifySum(path, True)
        local = self.verifySum(path, False)

        if remote is not local:
            self.kernel.logging.output('local file: '+str(local)+', remote: '+str(remote)+', for path: "' + path + '", "' + self.kernel.localDirectory + '/' + path + '"', 'plugins.checksum')
            return False

        return True



    def filterQueue(self, queuedItemState):
        """
        Verify queue in realtime

        :param args:
        :return:
        """

        if not queuedItemState:
            return queuedItemState

        # only if connection handler reported that all was successfuly sended
        if queuedItemState['state'] == 'finished' and queuedItemState['operationType'] == 'add' and queuedItemState['result']:
            if not self.compareFile(queuedItemState['virtualPath']):
                queuedItemState['result'] = False
                queuedItemState['state'] = 'failed'
                self.kernel.logging.output('Checksum failed on file '+queuedItemState['virtualPath'], 'plugins.checksum')

        return queuedItemState


    def __pluginInit__(self, args = ''):
        """
        Real plugin init after satisfying all dependencies
        :param args:
        :author: Damian Kęska
        :return:
        """

        # verify avaliable checksum commands on both sides
        self.verifyAvaliableCommands()
        self.enabled = True

        # initialize plugin after parsing arguments
        self.kernel.hooking.addOption('app.checkDestination.handlerSelection.done', self.checkRemoteHost, priority=97)

        # append plugin to iteration queue
        self.kernel.hooking.addOption('app.syncJob.Queue.iterate.item', self.filterQueue, priority=97)