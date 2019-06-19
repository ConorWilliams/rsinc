from time import sleep
import subprocess
import itertools


class SubPool():
    def __init__(self, max_workers):
        self.procs = []
        self.max_workers = 20

    def run(self, cmd):

        if len(self.procs) < self.max_workers:
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

            self.procs.pop(c).kill()
            self.run(cmd)

    def join(self):
        for c, proc in enumerate(self.procs):
            print('waiting', proc.args)
            proc.wait()
