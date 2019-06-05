#!/usr/bin/python3

'''
sinc.py

Copyright (c) 2019 C. J. Williams

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

# ****************************************************************************
# *                                 Settings                                 *
# ****************************************************************************


# where config and data files will be stored.
DRIVE_DIR = '/home/conor/two_way/'
BASE_R = 'onedrive:'               # root path of remote drive including colon.
BASE_L = '/home/conor/'            # path to local drive to mirror remote drive.

DEFAULT_DIRS = ['cpp', 'cam', 'docs']  # folders to sync when ran with -D flag

CASE_INSENSATIVE = True  # enables case checking for clouds (onedrive) that do
# not support upper case letters.

HASH_ON = True  # use hash and size to detect file changes, slows down code but
# improves accuracy.

HASH_NAME = 'SHA-1'  # name of hash function, run 'rclone lsjson --hash $path'
# to get supported hash functions from your cloud provider.

import argparse
import halo
import os
import subprocess
import time
import ujson as json

from clint.textui import colored
from datetime import datetime

# ****************************************************************************
# *                                  Classes                                 *
# ****************************************************************************

THESAME = 0
UPDATED = 1
DELETED = 2
CREATED = 3


class File():
    def __init__(self, name, uid, time, state=THESAME):
        self.name = name
        self.uid = uid
        self.time = time
        self.state = state
        self.moved = False


class Flat():
    def __init__(self):
        self.files = []
        self.uids = {}
        self.names = {}
        self.lower = set()

    def update(self, name, uid, time, state=THESAME):
        self.files.append(File(name, uid, time, state))
        self.uids.update({uid: self.files[-1]})
        self.names.update({name: self.files[-1]})
        self.lower.add(name.lower())


class Log(object):
    def __init__(self, path):
        self.path = path + "logs/"
        self.logs = []

        if not os.path.exists(self.path):
            subprocess.run(['mkdir', self.path])

    def __call__(self, log):
        self.logs.append(datetime.now().strftime('%H:%M:%S ') + log)

    def flush(self):
        day = datetime.now().strftime('%Y-%m-%d')
        log_file = open(self.path + day, "a+")

        for log in self.logs:
            log_file.write(log)

        log_file.close()


# ****************************************************************************
# *                                 Functions                                *
# ****************************************************************************


def calc_states(old, new):
    '''
    Calculates if files on one side have been updated, moved, deleted, 
    created or stayed the same. Arguments are both Flats.
    '''
    for name, file in new.names.items():
        if name in old.names:
            if old.names[name].uid != file.uid:
                file.state = UPDATED
            else:
                file.state = THESAME
        elif file.uid in old.uids:
            file.moved = True
            file.state = THESAME
        else:
            file.state = CREATED

    for name, file in old.names.items():
        if name not in new.names and file.uid not in new.uids:
            new.update(name, file.uid, file.time, DELETED)


def rename(path, name, flat):
    '''
    Renames file to be transferred if case conflict occurs on other side and 
    returns the new name
    '''
    new_name = name

    while CASE_INSENSATIVE and new_name.lower() in flat.lower:
        print(red('ERROR,'), 'case mismatch:', new_name + ', renaming')
        new_name = new_name.split('/')
        new_name[-1] = '_' + new_name[-1]
        new_name = '/'.join(new_name)

    if new_name != name:
        move(path + name, path + new_name)

    return new_name


def qt(string):
    return '"' + string + '"'


def read(file):
    '''Reads json do dict and returns dict'''
    with open(file, 'r') as fp:
        d = json.load(fp)

    return d


def write(file, d):
    '''Writes dict to json'''
    if not dry_run:
        with open(file, 'w') as fp:
            json.dump(d, fp, sort_keys=True, indent=2)


def lsl(path):
    '''
    Runs rclone lsjson on path and returns a dict containing each file with the
    size and last modified time as integers
    '''
    command = ['rclone', 'lsjson', '-R', '--files-only', path]

    if HASH_ON:
        command += ['--hash']

    result = subprocess.Popen(command, stdout=subprocess.PIPE)

    list_of_dicts = json.load(result.stdout)

    out = Flat()
    for d in list_of_dicts:
        time = d['ModTime'][:19]
        time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S").timestamp()

        if HASH_ON:
            hashsize = str(d['Size'])
            hashsize += d['Hashes'][HASH_NAME]
        else:
            hashsize = d['Size']

        out.update(d['Path'], hashsize, time)

    return out


''' ------------ Functions for working with packed dictionary's ------------ '''


def empty():
    '''Returns dict representing empty directory'''
    return {'fold': {}, 'file': {}}


def insert(nest, chain):
    '''Inserts element at the end of the chain into packed dict, nest'''
    if len(chain) == 2:
        nest['file'].update({chain[0]: chain[1]})
        return

    if chain[0] not in nest['fold']:
        nest['fold'].update({chain[0]: empty()})

    insert(nest['fold'][chain[0]], chain[1:])


def pack(flat):
    '''Converts flat, into packed dict'''
    nest = empty()
    for file in flat.files:
        chain = file.name.split(
            '/') + [{'uid': file.uid, 'datetime': file.time}]
        insert(nest, chain)

    return nest


def unpack(nest, flat, path=''):
    '''Converts packed dict, nest, into flat'''
    for k, v in nest['file'].items():
        flat.update(path + k, v['uid'], v['datetime'])

    for k, v in nest['fold'].items():
        unpack(v, flat, path + k + '/')


def _get_branch(nest, chain):
    '''Returns packed dict at end of chain in packed dict, nest'''
    if len(chain) == 0:
        return nest
    else:
        return _get_branch(nest['fold'][chain[0]], chain[1:])


def get_branch(nest, path):
    '''Helper function for _get_branch, converts path to chain'''
    return _get_branch(nest, path.split('/'))


def _merge(nest, chain, new):
    '''Merge packed dict, new, into packed dict, nest, at end of chain'''
    if len(chain) == 1:
        nest['fold'].update({chain[0]: new})
        return

    if chain[0] not in nest['fold']:
        nest['fold'].update({chain[0]: empty()})

    _merge(nest['fold'][chain[0]], chain[1:], new)


def merge(nest, path, new):
    '''Helper function for _merge, converts path to chain'''
    _merge(nest, path.split('/'), new)


def _have(nest, chain):
    '''Returns: true if chain is contained in packed dict, nest, else: false'''
    if chain[0] in nest['fold']:
        if len(chain) == 1:
            return 1
        else:
            return _have(nest['fold'][chain[0]], chain[1:])

    return 0


def have(master, path):
    '''Helper function for _have, converts path to chain'''
    return _have(master, path.split('/'))


def _get_min(nest, chain, min_chain):
    '''Returns the subset of chain contained in packed dict, nest'''
    if len(chain) == 1:
        return min_chain
    elif chain[0] not in nest['fold']:
        return min_chain
    else:
        min_chain.append(chain[1])
        return _get_min(nest['fold'][chain[0]], chain[1:], min_chain)


def get_min(master, path):
    '''Helper function for _get_min, converts path to chain'''
    chain = path.split('/')
    min_chain = _get_min(master, chain, [chain[0]])
    return '/'.join(min_chain)


''' ------------------- Functions for moving files about ------------------- '''


def move(source, dest):
    '''Move source to dest'''
    global counter
    counter += 1

    if not dry_run:
        print('%d/%d' % (counter, total_jobs) +
              ylw(' Move: ') + source + cyn(' to ') + dest)
        subprocess.run(['rclone', 'moveto', source, dest])
    else:
        print(ylw('Move: ') + source + cyn(' to ') + dest)


def cpyR(source, dest):
    '''Copy source (at local) to dest (at remote)'''
    global counter
    counter += 1

    if not dry_run:
        print('%d/%d' % (counter, total_jobs) + cyn(' Push: ') + source)
        subprocess.run(['rclone', 'copyto', source, dest])
    else:
        print(cyn("Push: ") + source)


def cpyL(dest, source):
    '''Copy source (at remote) to dest (at local)'''
    global counter
    counter += 1

    if not dry_run:
        print('%d/%d' % (counter, total_jobs) + mgt(' Pull: ') + source)
        subprocess.run(['rclone', 'copyto', source, dest])
    else:
        print(mgt("Pull: ") + source)


def null(*args):
    return


def conflict(source, dest):
    '''Duplicate, rename and copy conflicts both ways'''
    if skip:
        print(red('Skip conflict: ') + source)
        return

    print(red('Conflict: ') + source)

    if not dry_run:
        subprocess.run(['rclone', 'moveto', source, source + ".lcl_conflict"])
        subprocess.run(['rclone', 'moveto', dest, dest + ".rmt_conflict"])

    cpyR(source + ".lcl_conflict", dest + ".lcl_conflict")
    cpyL(source + ".rmt_conflict", dest + ".rmt_conflict")


def delL(left, right):
    '''Delete left (at local)'''
    global counter
    counter += 1

    if not dry_run:
        print('%d/%d' % (counter, total_jobs) + ylw(' Delete: ') + left)
        subprocess.run(['rclone', 'delete', left])
    else:
        print(ylw("Delete: ") + left)


def delR(left, right):
    '''Delete left (at remote)'''
    global counter
    counter += 1

    if not dry_run:
        print('%d/%d' % (counter, total_jobs) + ylw(' Delete: ') + right)
        subprocess.run(['rclone', 'delete', right])
    else:
        print(ylw("Delete: ") + right)


def r_sinc(lcl, rmt, path_lcl, path_rmt):
    '''Recovery sync function'''
    for name, file in lcl.names.items():
        if name in rmt.names:
            if file.uid != rmt.names[name].uid:
                if file.time > rmt.names[name].time:
                    cpyR(path_lcl + name, path_rmt + name)
                else:
                    cpyL(path_lcl + name, path_rmt + name)
        elif file.uid in rmt.uids:
            if file.time > rmt.uids[file.uid].time:
                move(path_rmt + rmt.uids[file.uid].name, path_rmt + name)
            else:
                move(path_lcl + name, path_lcl + rmt.uids[file.uid].name)
        else:
            new_name = rename(path_lcl, name, rmt)
            cpyR(path_lcl + name, path_rmt + name)

    for name, file in rmt.names.items():
        if name not in lcl.names and file.uid not in lcl.uids:
            new_name = rename(path_rmt, name, lcl)
            cpyL(path_lcl + name, path_rmt + name)


def sinc(old, lcl, rmt, path_lcl, path_rmt):
    '''Normal sync function'''
    if recover:
        r_sinc(lcl, rmt, path_lcl, path_rmt)
        return

    for name, file in sorted(lcl.names.items()):
        if file.state == CREATED:
            new_name = rename(path_lcl, name, rmt)
            cpyR(path_lcl + new_name, path_rmt + new_name)

        elif name in rmt.names:
            # Neither moved or both moved to same place
            LOGIC[file.state][rmt.names[name].state](
                path_lcl + name, path_rmt + name)

        elif file.moved == True:
            if file.uid in rmt.uids and rmt.uids[file.uid].moved == True:
                # Both moved to different places
                move(path_lcl + name, path_lcl + rmt.uids[file.uid].name)
            else:
                # Only lcl moved
                move(path_rmt + old.uids[file.uid].name, path_rmt + name)
                LOGIC[THESAME][rmt.names[old.uids[file.uid].name].state](
                    path_lcl + name, path_rmt + name)

        elif old.names[name].uid in rmt.uids:
            # Only rmt has moved
            rmt_name = rmt.uids[old.names[name].uid].name

            move(path_lcl + name, path_lcl + rmt_name)
            LOGIC[file.state][THESAME](path_lcl + rmt_name, path_rmt + rmt_name)

        else:
            print(red('WARNING:'), 'fell out of switch in sinc function')

    for name, file in sorted(rmt.names.items()):
        if file.state == CREATED:
            new_name = rename(path_rmt, name, lcl)
            cpyL(path_lcl + new_name, path_rmt + new_name)


# ****************************************************************************
# *                           Definitions / Set-up                           *
# ****************************************************************************


print('''
Copyright 2019 C. J. Williams (CHURCHILL COLLEGE)
This is free software with ABSOLUTELY NO WARRANTY''')

CWD = os.getcwd()
os.chdir(DRIVE_DIR)

cwd = CWD.split('/')

for elem in BASE_L.split('/')[:-1]:
    if cwd[0] == elem:
        cwd.pop(0)
    else:
        cwd = DEFAULT_DIRS
        break
else:
    if len(cwd) == 0:
        cwd = DEFAULT_DIRS
    else:
        cwd = ['/'.join(cwd)]

strtobool = {'yes': True, 'ye': True, 'y': True, 'n': False, 'no': False,
             1: 'yes', 0: 'no', 't': True, 'true': True, 'f': False,
             'false': False, 'Y': True, 'N': False, 'Yes': True, "No": False,
             '': True}

ylw = colored.yellow   # delete
cyn = colored.cyan     # push
mgt = colored.magenta  # pull
red = colored.red      # error/conflict
grn = colored.green    # normal info

spin = halo.Halo(spinner='dots', placement='right', color='yellow')

swap = str.maketrans("/", '_')

LOGIC = [
        [null, cpyL, delL, conflict],
        [cpyR, conflict, cpyR, conflict],
        [delR, cpyL, null, cpyL],
        [conflict, conflict, cpyR, conflict], ]


# ****************************************************************************
# *                             Parsing Arguments                            *
# ****************************************************************************


parser = argparse.ArgumentParser()

parser.add_argument("folders", help="folders to sync", nargs='*')
parser.add_argument("-s", "--skip", action="store_true", help="skip conflicts")
parser.add_argument("-d", "--dry", action="store_true", help="do a dry run")
parser.add_argument("-c", "--clean", action="store_true",
                    help="clean directories")
parser.add_argument("-D", "--default", help="sync defaults",
                    action="store_true")
parser.add_argument("-r", "--recovery", action="store_true",
                    help="enter recovery mode")
parser.add_argument("-a", "--auto", help="don't ask permissions",
                    action="store_true")

args = parser.parse_args()

if args.default:
    folders = DEFAULT_DIRS
elif args.folders == []:
    folders = cwd
else:
    folders = args.folders

dry_run = args.dry
auto = args.auto
skip = args.skip
recover = args.recovery

# ****************************************************************************
# *                               Main Program                               *
# ****************************************************************************


# get the master structure
if not os.path.exists('master.json'):
    print(ylw('WARN'), '"master.json" missing, this must be your first ever run')
    write('master.json', empty())

master = read('master.json')

if os.path.exists('TinySinc.tmp'):
    print(red('ERROR') + ', detected a crash, found TinySinc.tmp')
    corrupt = read('TinySinc.tmp')['folder']
    if corrupt in folders:
        folders.remove(corrupt)

    folders.insert(0, corrupt)
    recover = True

for folder in folders:
    print('')
    old = Flat()
    lcl = Flat()
    rmt = Flat()

    path = folder
    path_lcl = BASE_L + folder + '/'
    path_rmt = BASE_R + folder + '/'

    min_path = get_min(master, path)

    # Determine if first run
    if have(master, path):
        print(grn('Have:'), qt(path) + ', entering sync & merge mode')
    else:
        print(ylw('Don\'t have:'), qt(path) + ', entering first_sync mode')
        recover = True

    # Scan directories
    spin.start(("Crawling: ") + qt(path))

    lcl = lsl(path_lcl)
    rmt = lsl(path_rmt)

    spin.stop_and_persist(symbol='✔')

    # First run & recover mode
    if recover:
        print('Running', ylw('recover/first_sync'), 'mode')
    else:
        print('Reading last state.')

        branch = get_branch(master, path)
        unpack(branch, old)

        calc_states(old, lcl)
        calc_states(old, rmt)

    # Main logic
    dry_run = True
    counter = 0

    print(grn('Dry pass:'))
    sinc(old, lcl, rmt, path_lcl, path_rmt)

    dry_run = args.dry
    total_jobs = counter

    if dry_run:
        print('Found:', counter, 'job(s)')
    else:
        if counter == 0:
            print('Found:', counter, 'jobs')
        elif auto or strtobool[input('Execute? ')]:
            if not os.path.exists('TinySinc.tmp'):
                write('TinySinc.tmp', {'folder': folder})
            print(grn("Live pass:"))
            counter = 0
            sinc(old, lcl, rmt, path_lcl, path_rmt)

        # Merge into master and clean up
        if recover or counter != 0:
            spin.start(grn('Saving: ') + qt(min_path))

            merge(master, min_path, pack(lsl(BASE_L + min_path)))
            write('master.json', master)

            if args.clean:
                subprocess.run(["rclone", 'rmdirs', path_rmt])
                subprocess.run(["rclone", 'rmdirs', path_lcl])

            spin.stop_and_persist(symbol='✔')

        if os.path.exists('TinySinc.tmp'):
            subprocess.run(["rm", 'TinySinc.tmp'])

    recover = args.recovery

print('')
print(grn("All synced!"))
