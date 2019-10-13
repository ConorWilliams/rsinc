# Classes for rsinc module

import subprocess
import os

from time import sleep

THESAME, UPDATED, DELETED, CREATED = tuple(range(4))
NOMOVE, MOVED, CLONE, NOTHERE = tuple(range(4, 8))


class SubPool:
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
            while done is None:
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
                print("Error polled:", poll, "with", proc.args)
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


class File:
    """
    @brief      Class for to represent a file.
    """

    def __init__(self, name, uid, time, state, moved, is_clone, synced, ignore):
        self.name = name
        self.uid = uid
        self.time = time

        self.state = state
        self.moved = moved
        self.is_clone = is_clone
        self.synced = synced
        self.ignore = ignore

    def dump(self):
        """
        @brief      Get all properties accept name.

        @param      self  The object

        @return     All file properties accept name.
        """
        return (
            self.uid,
            self.time,
            self.state,
            self.moved,
            self.is_clone,
            self.synced,
            self.ignore,
        )


class Flat:
    def __init__(self, path):
        self.path = path
        self.names = {}
        self.uids = {}
        self.lower = set()
        self.dirs = set()

    def update(
        self,
        name,
        uid,
        time=0,
        state=THESAME,
        moved=False,
        is_clone=False,
        synced=False,
        ignore=False,
    ):

        self.names.update(
            {
                name: File(
                    name, uid, time, state, moved, is_clone, synced, ignore
                )
            }
        )
        self.lower.add(name.lower())

        d = os.path.dirname(name)
        d = os.path.join(self.path, d)
        self.dirs.add(d)

        if uid in self.uids:
            self.names[name].is_clone = True
            self.uids[uid].is_clone = True
            self.uids.update({uid: self.names[name]})
        else:
            self.uids.update({uid: self.names[name]})

    def clean(self):
        for file in self.names.values():
            file.synced = False

    def rm(self, name):
        if not self.names[name].is_clone:
            del self.uids[self.names[name].uid]

        del self.names[name]
        self.lower.remove(name.lower())

    def tag_ignore(self, regexs):
        # print(regexs)
        for name, file in self.names.items():
            if any(r.match(os.path.join(self.path, name)) for r in regexs):
                # print("ignore", os.path.join(self.path, name))
                file.ignore = True
            else:
                # print("NOT ignore", os.path.join(self.path, name))
                file.ignore = False

    def rm_ignore(self):
        for name, file in tuple(self.names.items()):
            if file.ignore:
                self.rm(name)


class Struct:
    def __init__(self):
        self.count = 0
        self.total = 0
        self.lcl = None
        self.rmt = None
        self.dry = True
        self.case = True
        self.pool = None
        self.rclone_flags = []
