import time
import libcopysync
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Watcher(FileSystemEventHandler):
    """ Watches for filesystem writes and passes events to copysync main class """
    
    directory = None
    app = None
    
    def startWatching(self, copysync):
        """ Start watching """
        
        self.copysync = copysync
        self.directory = copysync.localDirectory
        
        observer = Observer()
        observer.schedule(self, path=self.directory, recursive=True)
        observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        
        observer.join()
    
    
    def on_any_event(self, event):
        """ On modified event """

        # get instance of application
        self.copysync.appendToQueue(event.src_path)
