#-*- encoding: utf-8 -*-
import os
import sys
import subprocess
from dialog import Dialog

"""
Git integration plugin for copysync

:author: Damian Kęska
"""

class gitPlugin:
    dialog = None

    def __init__(self, app):
        self.dialog = Dialog(dialog="dialog")
        self.kernel = app
        self.kernel.interactive.recognizedChars['g'] = self.gitMenu

    def gitMenu(self):
        """
        Display a git menu
        :return:
        """

        ## make application output silently for a moment
        f = open(os.devnull, 'w')
        __stdout = sys.stdout
        sys.stdout = f

        code, tag = self.dialog.menu("Options",
                       choices=[("(1)", "Add untracked files to queue"),
                                ("(2)", "Cancel")])

        sys.stdout = __stdout

        if tag == '(1)':
            self.untrackedFilesMenu()



    def untrackedFilesMenu(self):
        """
        Display menu with list of untracked files to select to add to queue
        :return:
        """

        choices = []

        os.chdir(self.kernel.localDirectory)
        gitOutput = subprocess.check_output('git status', shell=True)

        posStart = gitOutput.find("(use \"git add <file>...\" to include in what will be committed)\n\n")
        untrackedBlock = gitOutput[posStart:]

        for line in untrackedBlock.split("\n")[2:]:
            if not line:
                break

            choices.append((str(line.replace("\t", '')), "", 1))

        code, tags = self.dialog.checklist("Select files:", choices=choices)

        if tags:
            for file in tags:
                self.kernel.appendToQueue(file)

