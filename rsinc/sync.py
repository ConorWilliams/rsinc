#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from copy import deepcopy

from .classes import SubPool
from .rclone import safe_push, safe_move, move, resolve_case, track
from .rclone import null, delL, delR, push, pull, conflict
from .colors import red

NUMBER_OF_WORKERS = 7

THESAME, UPDATED, DELETED, CREATED = tuple(range(4))
NOMOVE, MOVED, CLONE, NOTHERE = tuple(range(4, 8))

# Encodes logic for match states function.
LOGIC = [
    [null, pull, delL, conflict],
    [push, conflict, push, conflict],
    [delR, pull, null, pull],
    [conflict, conflict, push, conflict],
]


def calc_states(old, new):
    """
    @brief      Calculates if files on one side have been updated, moved,
                deleted, created or stayed the same.

    @param      old   Flat of the past state of a directory
    @param      old   Flat of the past state of a directory

    @return     None.
    """
    new_before_deletes = tuple(new.names.keys())

    for name, file in old.names.items():
        if name not in new.names and (file.uid not in new.uids
                                      or file.is_clone):
            # Want all clone-moves to leave delete place holders.
            new.update(name, file.uid, file.time, DELETED)

    for name in new_before_deletes:
        file = new.names[name]
        if name in old.names:
            if old.names[name].uid != file.uid:
                if file.uid in old.uids and not file.is_clone:
                    # degenatate double move
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


def sync(lcl,
         rmt,
         old=None,
         recover=False,
         dry_run=True,
         total=0,
         case=True,
         flags=[]):
    """
    @brief      Main sync function runs appropriate sync depending on arguments.

    @param      lcl      Flat of the lcl directory
    @param      rmt      Flat of the rmt directory
    @param      old      Flat of the past state of lcl and rmt
    @param      recover  Flag to run recovery sync
    @param      dry_run  Flag to do a dry run
    @param      total    The total number of operations the sync will require
    @param      case     Flag to enable case insensitive checking

    @return     The total number of jobs required, list of all (absolute)
                directories not in lcl or remote.
    """
    global track

    track.lcl = lcl.path
    track.rmt = rmt.path
    track.total = total
    track.dry = dry_run
    track.case = case
    track.count = 0
    track.pool = SubPool(NUMBER_OF_WORKERS)
    track.rclone_flags = flags

    cp_lcl = deepcopy(lcl)
    cp_rmt = deepcopy(rmt)

    if recover:
        match_states(cp_lcl, cp_rmt, recover=True)
        match_states(cp_rmt, cp_lcl, recover=True)
    else:
        match_moves(old, cp_lcl, cp_rmt)
        match_moves(old, cp_rmt, cp_lcl)

        cp_lcl.clean()
        cp_rmt.clean()
        track.pool.wait()

        match_states(cp_lcl, cp_rmt, recover=False)
        match_states(cp_rmt, cp_lcl, recover=False)

    track.pool.wait()

    dirs = (cp_lcl.dirs - lcl.dirs) | (cp_rmt.dirs - rmt.dirs)

    return track.count, dirs


def match_states(lcl, rmt, recover):
    """
    @brief      Basic sync of files in lcl to remote given all moves performed.
                Uses LOGIC array to determine actions, see bottom of file. If
                recover keeps newest file.

    @param      lcl      Flat of the lcl directory
    @param      rmt      Flat of the rmt directory
    @param      recover  Flag to use recovery logic

    @return     None.
    """
    names = sorted(lcl.names.keys())

    for name in names:
        file = lcl.names[name]

        if file.synced:
            continue

        file.synced = True

        if name in rmt.names:
            rmt.names[name].synced = True
            if not recover:
                LOGIC[file.state][rmt.names[name].state](name, name, lcl, rmt)
            elif file.uid != rmt.names[name].uid:
                if file.time > rmt.names[name].time:
                    push(name, name, lcl, rmt)
                else:
                    pull(name, name, lcl, rmt)
        elif file.state != DELETED:
            safe_push(name, lcl, rmt)
        else:
            print(red("WARN:"), 'unpaired deleted:', lcl.path, name)


def match_moves(old, lcl, rmt):
    """
    @brief      Mirrors file moves in lcl by moving files in rmt.

    @param      old   Flat of the past state of lcl and rmt
    @param      lcl   Flat of the lcl directory
    @param      rmt   Flat of the rmt directory

    @return     None.
    """
    global track

    names = sorted(lcl.names.keys())

    for name in names:
        if name not in lcl.names:
            # Caused by degenerate, double-move edge case triggering a rename.
            continue
        else:
            file = lcl.names[name]

        if file.synced or not file.moved:
            continue

        file.synced = True

        if name in rmt.names:
            rmt.names[name].synced = True

            if rmt.names[name].state == DELETED:
                # Can move like normal but will trigger rename and may trigger
                # unpaired delete warn.
                pass
            elif file.uid == rmt.names[name].uid:
                # Uids match therefore both moved to same place in lcl and rmt.
                continue
            elif rmt.names[name].moved:
                # Conflict, two moves to same place in lcl and remote. Could
                # trace their compliments and do something with them here.?
                file.state = UPDATED
                rmt.names[name].state = UPDATED
                continue
            elif name in old.names and (
                    old.names[name].uid in lcl.uids
            ) and lcl.uids[old.names[name].uid].moved:
                # This deals with the degenerate, double-move edge case.
                mvd_lcl = lcl.uids[old.names[name].uid]
                mvd_lcl.synced = True

                safe_move(name, mvd_lcl.name, rmt, lcl)
            else:
                # Not deleted, not supposed to be moved, not been moved.
                # Therefore rename rmt and procced with matching files move.
                nn = resolve_case(name, rmt)
                move(name, nn, rmt)
                # Must wait for rename
                track.pool.wait()

        trace, f_rmt = trace_rmt(file, old, rmt)

        if trace == NOMOVE:
            f_rmt.synced = True

            if f_rmt.state == DELETED:
                # Delete shy. Will trigger unpaired delete warn in match states.
                safe_push(name, lcl, rmt)
            else:
                # Move complimentary in rmt.
                safe_move(f_rmt.name, name, rmt, lcl)

        elif trace == MOVED:
            # Give preference to remote moves.
            f_rmt.synced = True
            safe_move(name, f_rmt.name, lcl, rmt)

        elif trace == CLONE:
            safe_push(name, lcl, rmt)

        elif trace == NOTHERE:
            # This should never happen?
            safe_push(name, lcl, rmt)


def trace_rmt(file, old, rmt):
    """
    @brief      Traces the state of file.

    @param      file  The file to trace (in lcl)
    @param      old   Flat of the past state of lcl and rmt
    @param      rmt   Flat of the rmt directory

    @return     State (NOMOVE, MOVED, CLONE or NOTHERE) of file in rmt, file
                object in rmt.
    """
    old_file = old.uids[file.uid]

    if old_file.name in rmt.names:
        rmt_file = rmt.names[old_file.name]

        if rmt.names[old_file.name].is_clone:
            if rmt.names[old_file.name].state == CREATED:
                trace = CLONE
            else:
                trace = NOMOVE
            return trace, rmt_file
        elif rmt.names[old_file.name].moved:
            # Do a uid trace
            pass
        else:
            return NOMOVE, rmt_file

    if old_file.uid in rmt.uids:
        rmt_file = rmt.uids[old_file.uid]

        if rmt.uids[old_file.uid].is_clone:
            trace = CLONE
        elif rmt.uids[old_file.uid].moved:
            trace = MOVED
        else:
            trace = NOMOVE
        return trace, rmt_file
    else:
        return NOTHERE, None
