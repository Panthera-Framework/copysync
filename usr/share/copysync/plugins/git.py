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
                       choices=[("(1)", "Add untracked/uncommited files to queue"),
                                ("(2)", "Clear backup files after merge"),
                                ("(3)", "Cancel")])

        if tag == '(1)':
            self.selectAllMenu(callback = self.notCommitedFilesMenu, notCommitedMenu = True)

        if tag == '(2)':
            self.clearFilesAfterMerge()

        sys.stdout = __stdout

    def clearFilesAfterMerge(self):
        """
        Clear files that stays after resolved merge conflict eg. with names ".orig" or ".LOCAL"
        :return:
        """

        os.chdir(self.kernel.localDirectory)
        subprocess.check_output('git clean -fd', shell=True)
        self.dialog.msgbox("Cleaned up git directory using 'git clean -fd'\nCurrent git status:\n"+subprocess.check_output('git status', shell=True), width=120, height=30)


    def selectAllMenu(self, callback, notCommitedMenu = False):

        choices = [
            ("(1)", "All positions checked"),
            ("(2)", "All positions unchecked")
        ]

        if notCommitedMenu:
            choices.append(("(3)", "Check only tracked"))
            choices.append(("(4)", "Check only not commited"))

        code, tag = self.dialog.menu("Start with", choices=choices)
        checked = 0

        if code > 0:
            return None

        if tag == '(1)':
            checked = 1

        if notCommitedMenu:
            if tag == '(3)':
                return callback(checked = 0, commitedChecked = 0, untrackedChecked = 1)
            elif tag == '(4)':
                return callback(checked = 0, commitedChecked = 1, untrackedChecked = 0)

        return callback(checked=checked)


    def notCommitedFilesMenu(self, checked = 1, commitedChecked = None, untrackedChecked = None):
        """
        Display menu with list of untracked files to select to add to queue
        :return:
        """

        choices = []

        os.chdir(self.kernel.localDirectory)
        gitOutput = subprocess.check_output('git status', shell=True)

        # untracked files
        if untrackedChecked is not None:
            checked = untrackedChecked

        posStart = gitOutput.find("(use \"git add <file>...\" to include in what will be committed)\n\n")
        untrackedBlock = gitOutput[posStart:]

        for line in untrackedBlock.split("\n")[2:]:
            if not line:
                break

            choices.append((str(line.replace("\t", '')), "(untracked)", checked))

        # not commited files
        if commitedChecked is not None:
            checked = commitedChecked

        posStart = gitOutput.find("to update what will be committed)\n")
        block = gitOutput[posStart:]

        for line in block.split("\n")[3:]:
            if not line:
                break

            choices.append((str(line.replace("\t", '').replace('modified:   ', '')), "", checked))

        if not choices:
            return self.gitMenu()

        code, tags = self.dialog.checklist("Select untracked files:", choices=choices, width=100, height=25, list_height=18)

        if tags:
            for file in tags:
                self.kernel.appendToQueue(file)
        else:
            self.gitMenu()
