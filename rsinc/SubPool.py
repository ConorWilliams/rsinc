from time import sleep
import subprocess


class SubPool():
    """
    @brief      Class to coordinate a pool of worker subprocess Processes
    """
    def __init__(self, max_workers):
        self.procs = []
        self.max_workers = max_workers

    def run(self, cmd):
        """
        @brief      Launch a subprocess to run a command.

        @param      self  The object
        @param      cmd   The command to run

        @return     None.
        """
        if len(self.procs) < self.max_workers:
            self.procs.append(subprocess.Popen(cmd))
            return
        else:
            done = None
            while done == None:
                done = self._find_done_process()

            self.procs.pop(done).terminate()
            self.run(cmd)

    def _find_done_process(self):
        """
        @brief      Finds a completed Process.

        @param      self  The object

        @return     Index of the completed Process.
        """
        for c, proc in enumerate(self.procs):
            poll = proc.poll()
            if poll == 0:
                return c
            elif poll is None:
                sleep(0.01)
                continue
            else:
                print('Error polled:', poll, 'with', proc.args)
                return c

        return None

    def wait(self):
        """
        @brief      Waits for all worker Processes to complete.

        @param      self  The object

        @return     None.
        """
        for proc in self.procs:
            proc.wait()
            proc.terminate()

        self.procs = []
