import os

"""
libnotify notification for copysync

:author: Damian Kęska
"""

class notifyPlugin:
    """
    libnotify notification for copysync

    :author: Damian Kęska
    """

    kernel = None

    def __init__(self, app):
        """
        Initialize - append callbacks to copysync functions
        :param app:
        :return:
        """

        self.kernel = app

        self.kernel.hooking.addOption('app.syncJob.Queue.iterate', self.queueAction, priority=99)
        self.kernel.hooking.addOption('app.syncJob.Queue.iterate.item', self.queueFileAction, priority=99)

    def queueAction(self, queueState):
        """
        On queue state changed hook
        :param queueState:
        :hook: app.syncJob.Queue.iterate
        :return:
        """

        if self.kernel.queue:
            os.system("notify-send -i /usr/share/icons/hicolor/64x64/apps/kate.png -u low 'copysync' 'Queued "+str(len(self.kernel.queue))+" files'")
        else:
            os.system("notify-send -i /usr/share/icons/hicolor/64x64/apps/kate.png -u low 'copysync' 'Queue finished'")

    def queueFileAction(self, queueState):
        """
        On file copy hook
        :param queueState:
        :hook: app.syncJob.Queue.iterate.item
        :return:
        """

        if not "state" in queueState:
            return None

        if os.path.isdir(queueState['file']):
            return None

        if queueState['state'] == 'finished':
            if queueState['result']:
                os.system("notify-send -i /usr/share/icons/hicolor/64x64/apps/kate.png -u low 'copysync' '"+os.path.basename(queueState['file'])+" sent'")
            else:
                os.system("notify-send -i /usr/share/icons/hicolor/64x64/apps/kate.png -u low 'copysync' 'Cannot send "+os.path.basename(queueState['file'])+"'")