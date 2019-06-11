#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import ujson as json
import logging
from datetime import datetime

from clint.textui import colored

cyn = colored.cyan     # in / to lcl
mgt = colored.magenta  # in / to rmt
ylw = colored.yellow   # delete
red = colored.red      # conflict

THESAME, UPDATED, DELETED, CREATED = tuple(range(4))
NOMOVE, MOVED, CLONE, NOTHERE, MOVED_N, MOVED_U = tuple(range(6))

log = logging.getLogger(__name__)

# ****************************************************************************
# *                                  Classes                                 *
# ****************************************************************************


class File():
    def __init__(self, name, uid, time, state):
        self.name = name
        self.uid = uid
        self.time = time
        self.state = state
        self.moved = False
        self.is_clone = False
        self.synced = False


class _Flat():
    def __init__(self, path):
        self.path = path
        self.files = []
        self.uids = {}
        self.names = {}
        self.lower = set({})

    def update(self, name, uid, time, state=THESAME):
        self.files.append(File(name, uid, time, state))
        self.names.update({name: self.files[-1]})
        self.lower.add(name.lower())

        if uid in self.uids:
            self.names[name].is_clone = True
            self.uids[uid].is_clone = True
        else:
            self.uids.update({uid: self.files[-1]})

    def file_update(file, name)
        self.files.append(file)
        self.files[-1].name = name

        self.names.update({name: self.files[-1]})
        self.lower.add(name.lower())

        if file.uid in self.uids:
            self.names[name].is_clone = True
            self.uids[file.uid].is_clone = True
        else:
            self.uids.update({file.uid: self.files[-1]})


class Flat(_Flat):
    def __init__(self, path):
        _Flat.__init__(self, path)
        self.tmp = _Flat(path)

    def clean(self):
        self.tmp = _Flat(self.path)
        for file in self.files:
            file.synced = False


class Struct():
    def __init__(self):
        self.count = 0
        self.total = 0
        self.lcl = None
        self.rmt = None
        self.dry = True
        self.case = True


track = Struct()  # global used to track how many operations sync needs

# ****************************************************************************
# *                                 Functions                                *
# ****************************************************************************


def lsl(path, hash_name):
    '''
    Runs rclone lsjson on path and returns a Flat containing each file with the
    uid and last modified time
    '''
    command = ['rclone', 'lsjson', '-R', '--files-only', '--hash', path]

    subprocess.run(['rclone', 'mkdir', path])
    result = subprocess.Popen(command, stdout=subprocess.PIPE)
    list_of_dicts = json.load(result.stdout)

    out = Flat(path)
    for d in list_of_dicts:
        time = d['ModTime'][:19]
        time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S").timestamp()

        hashsize = str(d['Size'])
        hashsize += d['Hashes'][hash_name]

        out.update(d['Path'], hashsize, time)

    return out


def prepend(name, prefix):
    '''
    Adds 'prefix' to the begging of the file name, 'name' and returns the new
    name
    '''
    new_name = name.split('/')
    new_name[-1] = prefix + new_name[-1]
    new_name = '/'.join(new_name)
    return new_name


def calc_states(old, new):
    '''
    Calculates if files on one side have been updated, moved, deleted,
    created or stayed the same. Arguments are both Flats.
    '''
    new_before_deletes = set(new.names.keys())

    for name, file in old.names.items():
        if name not in new.names and (file.uid not in new.uids or file.is_clone):
            # Want all clone-moves to leave delete place holders
            new.update(name, file.uid, file.time, DELETED)

    for name in new_before_deletes:
        file = new.names[name]
        if name in old.names:
            if old.names[name].uid != file.uid:
                if file.uid in old.uids and not file.is_clone:
                    file.moved = True
                    file.state = THESAME
                else:
                    file.state = UPDATED
            else:
                file.state = THESAME
        elif file.uid in old.uids and not file.is_clone:
            file.moved = True
            file.state = THESAME
        else:
            file.state = CREATED


def sync(lcl, rmt, old=None, recover=False, dry_run=True, total=0, case=True):
    global track

    track.lcl = lcl.path
    track.rmt = rmt.path
    track.total = total
    track.dry = dry_run
    track.case = case
    track.count = 0

    if recover:
        recover(lcl, rmt)
        recover(rmt, lcl)
    else:
        match_moves(old, lcl, rmt)
        match_moves(old, rmt, lcl)
        sync_states(old, lcl, rmt)
        sync_states(old, rmt, lcl)

    lcl.clean()
    rmt.clean()

    return track.count


def match_moves(old, lcl, rmt)
    names = set(lcl.names.keys())

    new_lcl = Flat(lcl.path)
    new_rmt = Flat(rmt.path)

    for name, file in sorted(lcl.name.items()):
        if file.synced or not file.moved:
            new_lcl.file_update(file, name)
            continue

        if name in rmt.names:
            if rmt.names[name].state == DELETED:
                pass
            elif name in old.names and lcl.uids[old.names[name].uid].moved:
                mvd_lcl = lcl.uids[old.names[name].uid]
                tmv_rmt = rmt.names[name]
                if not tmv_rmt.synced:
                    tmv_rmt.synced = True
                    mvd_lcl.synced = True
                    nn = safe_move(name, mvd_lcl.name, rmt)
                    nn = balance_names(mvd_lcl.name, nn, lcl, rmt)
                    new_lcl.file_update(mvd_lcl, nn)
                    new_rmt.file_update(tmv_rmt, nn)
            else:
                rmt.names[name].synced = True
                file.state = CREATED
                new_lcl.file_update(file, name)
                continue

        t, f_rmt = trace(file, old, rmt)

        if t == NOMOVE:
            f_rmt.synced = True
            if f_rmt.state == DELETED:
                nn = safe_push(name, name, lcl, rmt)
            else:
                nn = safe_move(f_rmt.name, name, rmt)
                nn = balance_names(name, nn, lcl, rmt)

        elif t == MOVED_U:
            f_rmt.synced = True
            nn = safe_move(name, f_rmt.name, lcl)
            nn = balance_names(nn, f_rmt.name, lcl, rmt)
            LOGIC[file.state][f_rmt.state](nn, nn, lcl, rmt)

        elif t == MOVED_N or CLONE or NOTHERE:
            safe_push(name, name, lcl, rmt)


def trace_rmt(file, old, rmt):
    old_file = old.uids[file.uid]

    if old_file.is_clone:
        # Can't track clones by uid, returning CLONE forces push
        return CLONE, '?'

    if old_file.name in rmt.names:
        rmt_file = rmt.names[old_file.name]

        if rmt.names[old_file.name].is_clone:
            if mt.names[old_file.name].state == CREATED:
                trace = CLONE
            else:
                trace = NOMOVE
        elif rmt.names[old_file.name].moved:
            trace = MOVED_N
        else:
            trace = NOMOVE
    elif old_file.uid in rmt.uids:
        rmt_file = rmt.uids[old_file.uid]

        if rmt.uids[old_file.uid].is_clone:
            trace = CLONE
        elif rmt.uids[old_file.uid].moved:
            trace = MOVED_U
        else:
            trace = NOMOVE
    else:
        trace = NOTHERE

    return trace, rmt_file


def recover(lcl, rmt):
    for name, file in sorted(lcl.names.items()):
        if file.synced:
            continue
        elif name in rmt.names:
            if file.uid != rmt.names[name].uid:
                if file.time > rmt.names[name].time:
                    push(name, name, lcl, rmt)
                else:
                    pull(name, name, lcl, rmt)
            rmt.names[name].synced = True
        else:
            safe_push(name, name, lcl, rmt)


def balance_names(name_lcl, name_rmt, lcl, rmt):
    '''
    Used to match names when a case-conflict-rename generates name 
    differences between local and remote
    '''
    nn_lcl = name_lcl
    nn_rmt = name_rmt

    while nn_lcl != nn_rmt:
        if len(nn_lcl) > len(nn_rmt):
            nn_rmt = nn_lcl
        else:
            nn_lcl = nn_rmt

        resolve_case(nn_lcl, lcl)
        resolve_case(nn_rmt, rmt)

    if nn_lcl != name_lcl:
        safe_move(name_lcl, nn_lcl, lcl)
    if nn_rmt != name_rmt:
        safe_move(name_rmt, nn_rmt, rmt)

    return nn_lcl


def resolve_case(name, flat):
    '''
    Detects if 'name_s' has any case conflicts in any of the Flat()'s in 
    'flat_d'. If it does name is modified until no case conflicts occur and the 
    new name returned
    '''
    global track

    new_name = name

    if track.case:
        while new_name.lower() in flat.lower or new_name.lower() in flat.tmp.lower:
            new_name = prepend(new_name, '_')
    else:
        while new_name in flat.names or new_name in flat.tmp.names:
            new_name = prepend(new_name, '_')

    return new_name


def safe_push(name_s, name_d, flat_s, flat_d):
    nn = resolve_case(name_s, flat_d)
    push(name_s, nn, flat_s, flat_d)
    nn = balance_names(name_s, nn, flat_s, flat_d)
    flat_d.tmp.update(nn, 'null', 0)
    return nn


def safe_move(name_s, name_d, flat):
    '''Move source to dest'''
    global track
    track.count += 1

    nn_d = resolve_case(name_d, flat)
    base = flat.path

    if base == track.lcl:
        col = cyn
    elif base == track.rmt:
        col = mgt

    info = col('Move') + '(%s): ' % base + name_s + col(' to: ') + nn_d

    if not track.dry:
        print('%d/%d' % (track.count, track.total), info)
        log.info('MOVE(%s): %s TO %s', base, name_s, nn_d)
        subprocess.run(['rclone', 'moveto', base + name_s, base + nn_d])
    else:
        print(info)

    flat.tmp.update(nn_d, 'null', 0)

    return nn_d


def push(name_s, name_d, flat_s, flat_d):
    global track
    track.count += 1

    if flat_s.path == track.lcl and flat_d.path == track.rmt:
        text = 'Push'
        col = mgt

    elif flat_s.path == track.rmt and flat_d.path == track.lcl:
        text = 'Pull'
        col = cyn

    info = col('%s: ' % text) + name_d

    if not track.dry:
        print('%d/%d' % (track.count, track.total), info)
        log.info('%s: %s', text.upper(), name_d)
        cmd = ['rclone', 'copyto', flat_s.path + name_s, flat_d.path + name_d]
        subprocess.run(cmd)
    else:
        print(info)


def pull(name_s, name_d, flat_s, flat_d):
    '''Copy source (at remote) to dest (at local)'''
    push(name_d, name_s, flat_d, flat_s)


def conflict(name_s, name_d, flat_s, flat_d):
    '''Rename and copy conflicts both ways'''
    global track

    print(red('Conflict') + ' %d:%d: %s' % (flat_s.names[name_s].state,
                                            flat_d.names[name_d].state,
                                            name_s),)

    if not track.dry:
        log.warning('CONFLICT: %s', name_s)

    nn_lcl = safe_move(name_s, prepend(name_s, 'lcl_'), flat_s)
    nn_rmt = safe_move(name_d, prepend(name_d, 'rmt_'), flat_d)

    safe_push(nn_lcl, nn_lcl, flat_s, flat_d)
    safe_push(nn_rmt, nn_rmt, flat_d, flat_s)


def delL(name_s, name_d, flat_s, flat_d):
    '''Delete local (at local)'''
    global track
    track.count += 1

    info = ylw('Delete: ') + flat_s.path + name_s

    if not track.dry:
        print('%d/%d' % (track.count, track.total), info)
        log.info('DELETE: %s', flat_s.path + name_s)
        subprocess.run(['rclone', 'delete', flat_s.path + name_s])
    else:
        print(info)


def delR(name_s, name_d, flat_s, flat_d):
    '''Delete remote (at remote)'''
    delL(name_d, name_s, flat_d, flat_s)


def null(*args):
    return


LOGIC = [[null, pull, delL, conflict],
         [push, conflict, push, conflict],
         [delR, pull, null, pull],
         [conflict, conflict, push, conflict], ]
