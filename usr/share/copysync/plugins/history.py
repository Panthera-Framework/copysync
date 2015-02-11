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

    history = ''

    def __init__(self, app):
        """
        Initialize - append callbacks to copysync functions
        :param app:
        :return:
        """

        self.kernel = app
        self.dialog = Dialog(dialog="dialog")

        # hook up to queue
        self.kernel.hooking.addOption('app.syncJob.Queue.iterate.item', self.queueFileAction, priority=10)

        # hook up to interactive console
        if self.kernel.interactive:
            self.kernel.interactive.recognizedChars['h'] = self.showHistoryWindow

    def queueFileAction(self, args):
        """
        Capture queue actions to put into history log
        """


        if not 'operationType' in args or not args['operationType']:
            return args

        self.history += "["+time.strftime("%d.%m.%Y %H:%M:%S")+"] " + args['operationType'] + " " +args['virtualPath']+ "\n"

        return args

    def showHistoryWindow(self):
        """
        Show history window using Dialog
        :return:
        """


        f = open(os.devnull, 'w')
        __stdout = sys.stdout
        sys.stdout = f

        self.dialog.msgbox(self.history, width=160, height=30)

        # restore stdout
        sys.stdout = __stdout