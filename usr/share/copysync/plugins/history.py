#-*- encoding: utf-8 -*-
import os
import sys
from dialog import Dialog
import time

"""
Simple history showing plugin for copysync

:author: Damian Kęska <damian.keska@fingo.pl>
"""

class historyPlugin:
    """
    Simple history showing plugin for copysync

    :author: Damian Kęska <damian.keska@fingo.pl>
    """

    history = list()

    def __init__(self, app):
        """
        Initialize - append callbacks to copysync functions
        :param app:
        :author: Damian Kęska <damian.keska@fingo.pl>
        :return:
        """

        self.kernel = app
        self.dialog = Dialog(dialog="dialog")

        # hook up to queue
        self.kernel.hooking.addOption('app.syncJob.Queue.iterate.item', self.queueFileAction, priority=10)

        # hook up to args init
        self.kernel.hooking.addOption('app.argsparsing.init', self.initializeInteractive, priority=99)


    def initializeInteractive(self, args = ''):
        """
        hook up to interactive console

        :param args:
        :author: Damian Kęska <damian.keska@fingo.pl>
        :return:
        """

        # hook up to interactive console
        if self.kernel.interactive:
            self.kernel.interactive.recognizedChars['h'] = self.showHistoryWindow

    def queueFileAction(self, args = ''):
        """
        Capture queue actions to put into history log

        :param dict args: Input queue state parameters
        :author: Damian Kęska <damian.keska@fingo.pl>
        :return: input args
        """

        if not 'operationType' in args or not args['operationType']:
            return args

        # mapping:
        # 0 => date
        # 1 => operation type (eg. add, remove)
        # 2 => virtual path

        self.history.append((time.strftime("%d.%m.%Y %H:%M:%S"), args['operationType'], args['virtualPath']))

        return args

    def showHistoryWindow(self):
        """
        Show history window using Dialog
        :return:
        """


        f = open(os.devnull, 'w')
        __stdout = sys.stdout
        sys.stdout = f

        historyString = ''

        for entry in self.history:
            historyString += "["+entry[0]+"] "+entry[1]+": "+entry[2]+" \n"

        self.dialog.msgbox(historyString, width=160, height=30)

        # restore stdout
        sys.stdout = __stdout