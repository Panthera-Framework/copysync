#-*- encoding: utf-8 -*-

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

        # initialize plugin after parsing arguments
        #self.kernel.hooking.addOption('app.argsparsing.init', self.__pluginInit__, priority=97)


    def addArgsParsingArguments(self, argsParsing):
        """
        Add arguments to argsparsing

        :param argsParsing: Object
        :author: Damian Kęska
        :return:
        """

        argsParsing.createArgument('--verify-checksum', '-s', self.__pluginInit__, 'Verify checksum after file upload', action='store_true', required=False)

    def verifyAvaliableCommands(self):
        """
        This function is verifying if same hashing functions are avaliable at both source and destination

        :author: Damian Kęska
        :return:
        """

        return True

    def __pluginInit__(self, args = ''):
        """
        Real plugin init after satisfying all dependencies
        :param args:
        :author: Damian Kęska
        :return:
        """

        # verify avaliable checksum commands on both sides
        self.verifyAvaliableCommands()