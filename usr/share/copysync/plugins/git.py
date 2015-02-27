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
    lastQueueLock = 0
    __gitFilesCount = 0
    currentBranch = ""

    def __init__(self, app):
        """
        Constructor of a plugin
        :param app: Panthera Framework based application main class object
        :return:
        """

        self.kernel = app

        # hook up to args init
        self.kernel.hooking.addOption('app.argsparsing.init', self.__pluginInit__, priority=98)

    def __pluginInit__(self, args = ''):
        """
        Initialize the plugin after all dependencies are met

        :param args:
        :return:
        """

        ## list all remotes at initialization
        remotes = self._gitCommand('remote -v')

        for remote in remotes.replace("\t", ' ').replace('  ', ' ').split("\n"):
            parts = remote.split(' ')

            if len(parts) < 3:
                continue

            self.kernel.logging.output('Detected git remote: '+parts[1]+' '+parts[2], 'git')


        if "fatal:" in remotes:
            self.kernel.logging.output('Git responded with a fatal error, '+remotes, 'git')
            return False

        ## check branch to display at init
        status = self._gitCommand('status').split("\n")
        self.currentBranch = self._gitCommand('rev-parse --abbrev-ref HEAD')

        self.kernel.logging.output(status[0], 'git')

        ## initialize interface
        self.dialog = Dialog(dialog="dialog")

        if self.kernel.interactive:
            self.kernel.interactive.recognizedChars['g'] = self.gitMenu

        ## hook up to queue (to hold on application on branch change)
        self.kernel.hooking.addOption('app.syncJob.Queue.append.before', self.queueAppendAction, priority=10)


    def queueAppendAction(self, status):
        """
        On appending to queue
        :param status:
        :return:
        """

        if self.kernel.queueLock:
            status[0] = True

        if '.git' in status[2]:
            self.__gitFilesCount = self.__gitFilesCount + 1

            if self.kernel.queueLock:
                self.kernel.logging.output('Removing git lock', 'git')
                self.kernel.queueLock = False

            status[0] = True
        else:
            if self.__gitFilesCount > 4:
                branch = self._gitCommand('rev-parse --abbrev-ref HEAD')

                if branch != self.currentBranch:
                    self.kernel.logging.output('Creating git lock, as branch changed', 'git')
                    self.kernel.queueLock = True

                self.currentBranch = branch

            self.__gitFilesCount = 0

        return status


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
                                ("(3)", "Revert commits"),
                                ("(4)", "Clear backup files after merge"),
                                ("(5)", "Cancel")])

        if tag == '(1)':
            self.selectAllMenu(callback = self.notCommitedFilesMenu, notCommitedMenu = True)

        elif tag == '(2)':
            self.commitsMenu()

        elif tag == '(3)':
            self.commitsMenu(revert = True)

        elif tag == '(4)':
            self.clearFilesAfterMerge()

        sys.stdout = __stdout


    def commitsMenu(self, revert = False):
        """
        Recent commits menu
        Allows selecting commits to build list of files and send from selected revisions

        :author: Damian Kęska <damian.keska@fingo.pl>
        :return: None
        """

        commits = list()
        choices = []
        log = self._gitCommand('--no-pager log --oneline')
        i = 0

        for line in log.split("\n"):
            i = i + 1
            separator = line.find(' ')
            commits.append({'id': line[0:separator], 'title': line[(separator+1):], 'number': i})
            choices.append(("("+line[0:separator]+")", line[(separator+1):], 0))

        if revert:
            code, tag = self.dialog.checklist("Revert commits (total: "+str(len(commits))+")", choices=choices, width=120, height=20, list_height=10)
        else:
            code, tag = self.dialog.checklist("Submit commits (total: "+str(len(commits))+")", choices=choices, width=120, height=20, list_height=10)

        if tag:
            if revert:
                return self._appendCommitRevertFiles(commits, selected=tag)

            ## array of fileName => contents
            files = {}
            i = 0

            for commitID in tag:
                i = i + 1
                commitID = commitID.replace('(', '').replace(')', '')

                filesList = self._gitCommand('diff-tree --no-commit-id --name-only -r '+commitID)

                if "fatal:" in filesList:
                    self.kernel.logging.output('Cannot get list of files for revision '+commitID, 'git')
                    continue

                self._appendCommitFiles(commitID, filesList, files, commitNumber = i)


    def _appendCommitRevertFiles(self, commits, selected):
        """
        Append revert of commits

        :param commits: List of all avaliable commits
        :param selected: Selected commits
        :return:
        """

        selectedList = list()
        filesList = {}

        # strip "(" and ")" from commits list
        for commit in selected:
            selectedList.append(commit.replace('(', '').replace(')', ''))

        # we have to preserve list order
        for commit in commits:
            # if commit was selected, and its not a first commit
            if commit['number'] < 2 or not (commit['id'] in selectedList):
                continue

            currentCommitFilesList = self._gitCommand('diff-tree --no-commit-id --name-only -r '+commit['id']).split("\n")
            previousCommitID = commits[commit['number']-2]['id']

            for file in currentCommitFilesList:
                try:
                    filesList[file] = self._gitCommand('show '+previousCommitID+':'+file)
                except Exception as e:
                    # file propably removed
                    filesList[file] = False
                    self.kernel.appendToQueue(file, forceRemove = True)
                    continue

        ## append oldest versions of files
        for file, contents in filesList.iteritems():
            self.kernel.appendToQueue(file, contents = contents)





    def clearFilesAfterMerge(self):
        """
        Clear files that stays after resolved merge conflict eg. with names ".orig" or ".LOCAL"

        :author: Damian Kęska <damian.keska@fingo.pl>
        :return: None
        """

        self._gitCommand('clean -fd')

        # TODO: Confirmation using clean -n (dry run)
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




    def _appendCommitFiles(self, commitID, filesList, files, commitNumber):
        """
        Helper method for commitsMenu()
        Appends commited files to queue

        :param commitID:
        :param filesList:
        :param files: "Global" array with list of files we already appended
        :return: files array
        """

        for file in filesList.split("\n"):
            if not file or not os.path.isfile(self.kernel.localDirectory + "/" + file):
                continue

            if not file in files:
                files[file] = self._gitCommand('show '+commitID+':'+file)

                tmp = open(file, 'r')
                self.kernel.appendToQueue(file, tmp.read())
                tmp.close()

        return files


    def _gitCommand(self, command):
        """
        Execute a git command
        :param string command: Command line query string
        :return: string
        """

        os.chdir(self.kernel.localDirectory)
        return subprocess.check_output('git '+command, shell = True)