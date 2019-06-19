from time import sleep
import subprocess
import itertools


class SubPool():
    def __init__(self, default_workers):
        self.procs = []
        self.workers = default_workers
        self.default_workers = default_workers

    def run(self, cmd, tmp_workers=None):
        if tmp_workers != None:
            self.workers = tmp_workers
        else:
            self.workers = self.default_workers

        if len(self.procs) < self.workers:
            self.procs.append(subprocess.Popen(cmd))
            #print('appended', self.procs[-1].args)
            return
        else:
            for c, proc in itertools.cycle(enumerate(self.procs)):
                poll = proc.poll()
                if poll == 0:
                    break
                elif poll == None:
                    #print('sleep', proc.args)
                    sleep(0.1)
                    continue
                else:
                    print('Error polled:', poll, 'with', proc.args)
                    break

            self.procs.pop(c).terminate()
            self.run(cmd)

    def wait(self):
        for c, proc in enumerate(self.procs):
            #print('waiting', proc.args)
            proc.wait()
