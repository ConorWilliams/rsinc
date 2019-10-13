# Classes for rsinc module

import subprocess
import os

from time import sleep

THESAME, UPDATED, DELETED, CREATED = tuple(range(4))
NOMOVE, MOVED, CLONE, NOTHERE = tuple(range(4, 8))


class File:
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
        for name, file in self.names.items():
            if any(r.match(os.path.join(self.path, name)) for r in regexs):
                file.ignore = True
            else:
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


class SubPool:
    def __init__(self, max_workers):
        self.procs = []
        self.max_workers = max_workers

    def run(self, cmd):

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

        for proc in self.procs:
            proc.wait()
            proc.terminate()

        self.procs = []
