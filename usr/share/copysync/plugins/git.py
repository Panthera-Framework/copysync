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
        """
        Constructor of a plugin
        :param app: Panthera Framework based application main class object
        :return:
        """

        self.kernel = app

        ## list all remotes at initialization
        remotes = self._gitCommand('remote -v')

        for remote in remotes.replace("\t", ' ').replace('  ', ' ').split("\n"):
            parts = remote.split(' ')

            if len(parts) < 3:
                continue

            app.logging.output('Detected git remote: '+parts[1]+' '+parts[2], 'git')


        if "fatal:" in remotes:
            app.logging.output('Git responded with a fatal error, '+remotes, 'git')
            return False

        ## check branch to display at init
        status = self._gitCommand('status').split("\n")

        app.logging.output(status[0], 'git')


        self.dialog = Dialog(dialog="dialog")
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
                                ("(2)", "Send commits"),
                                ("(3)", "Clear backup files after merge"),
                                ("(4)", "Cancel")])

        if tag == '(1)':
            self.selectAllMenu(callback = self.notCommitedFilesMenu, notCommitedMenu = True)

        elif tag == '(2)':
            self.commitsMenu()

        elif tag == '(3)':
            self.clearFilesAfterMerge()

        sys.stdout = __stdout


    def commitsMenu(self):
        """
        Recent commits menu
        Allows selecting commits to build list of files and send from selected revisions

        :author: Damian Kęska <damian.keska@fingo.pl>
        :return: None
        """

        commits = {}
        choices = []
        log = self._gitCommand('--no-pager log --oneline')

        for line in log.split("\n"):
            separator = line.find(' ')
            commits[line[0:separator]] = line[(separator+1):]
            choices.append(("("+line[0:separator]+")", line[(separator+1):], 0))

        code, tag = self.dialog.checklist("Submit commits (total: "+str(len(commits))+")", choices=choices, width=120, height=20, list_height=10)

        if tag:
            ## array of fileName => contents
            files = {}

            for commitID in tag:
                commitID = commitID.replace('(', '').replace(')', '')

                filesList = self._gitCommand('diff-tree --no-commit-id --name-only -r '+commitID)

                if "fatal:" in filesList:
                    self.kernel.logging.output('Cannot get list of files for revision '+commitID, 'git')
                    continue

                for file in filesList.split("\n"):
                    if not file or not os.path.isfile(self.kernel.localDirectory + "/" + file):
                        continue

                    if not file in files:
                        files[file] = self._gitCommand('show '+commitID+':'+file)

                        tmp = open(file, 'r')
                        self.kernel.appendToQueue(file, tmp.read())
                        tmp.close()




    def _gitCommand(self, command):
        """
        Execute a git command
        :param string command: Command line query string
        :return: string
        """

        os.chdir(self.kernel.localDirectory)
        return subprocess.check_output('git '+command, shell = True)

    def clearFilesAfterMerge(self):
        """
        Clear files that stays after resolved merge conflict eg. with names ".orig" or ".LOCAL"

        :author: Damian Kęska <damian.keska@fingo.pl>
        :return: None
        """

        self._gitCommand('clean -fd')
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
        gitOutput = self._gitCommand('status')

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
