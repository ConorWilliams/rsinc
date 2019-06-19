from time import sleep
import subprocess
import itertools


class SubPool():
    def __init__(self, max_workers):
        self.procs = []
        self.max_workers = max_workers

    def run(self, cmd):
        if len(self.procs) < self.max_workers:
            self.procs.append(subprocess.Popen(cmd))
            #print('appended', self.procs[-1].args)
            return
        else:
            done = None
            while done == None:
                done = __find_done_process()

            self.procs.pop(done).terminate()
            self.run(cmd)

    def __find_done_process(self):
        for c, proc in enumerate(self.procs):
            poll = proc.poll()
            if poll == 0:
                return c
            elif poll == None:
                #print('sleep', proc.args)
                sleep(0.1)
                continue
            else:
                print('Error polled:', poll, 'with', proc.args)
                return c

        return None

    def wait(self):
        for proc in self.procs:
            #print('waiting', proc.args)
            proc.wait()
            proc.terminate()

        self.procs = []
