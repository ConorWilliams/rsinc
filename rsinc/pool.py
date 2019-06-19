from multiprocessing import Process, Queue
from time import sleep
import subprocess


class SubPool():
    def __init__(self, max_workers):
        self.queue = Queue()
        self.workers = []

        for _ in range(max_workers):
            self.workers.append(Process(target=thread, args=(self.queue, )))

        for t in self.workers:
            t.start()

    def run(self, command):

        while not self.queue.empty():
            print('sleepy')
            sleep(0.1)

        self.queue.put(command)

        return

    def join(self):
        for _ in range(len(self.workers)):
            self.queue.put(None)

        for t in self.workers:
            t.join()


def thread(queue):
    while True:
        cmd = queue.get()

        if cmd == None:
            return 0
        else:
            subprocess.run(cmd)
