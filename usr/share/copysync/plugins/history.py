"""
Simple history showing plugin for copysync

:author: Damian Kęska <damian.keska@fingo.pl>
"""

class historyPlugin:
    """
    Simple history showing plugin for copysync

    :author: Damian Kęska <damian.keska@fingo.pl>
    """

    def __init__(self, app):
        """
        Initialize - append callbacks to copysync functions
        :param app:
        :return:
        """

        self.kernel = app

        self.kernel.hooking.addOption('app.syncJob.Queue.iterate', self.queueAction, priority=99)
        self.kernel.hooking.addOption('app.syncJob.Queue.iterate.item', self.queueFileAction, priority=99)