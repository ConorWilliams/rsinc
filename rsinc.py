#!/usr/bin/python3

# ****************************************************************************
# *                                 Settings                                 *
# ****************************************************************************


DRIVE_DIR = '/home/conor/rsinc/'  # Where config and data files will be stored
BASE_R = 'onedrive:'             # Root path of remote drive including colon
BASE_L = '/home/conor/'          # Path to local drive to mirror remote drive

DEFAULT_DIRS = ['cpp', 'cam', 'docs']  # Folders to sync when ran with -D flag

CASE_INSENSATIVE = True  # Enables case checking for clouds (onedrive) that do
                         # not support upper case letters

HASH_NAME = 'SHA-1'  # Name of hash function, run 'rclone lsjson --hash $path'
                     # to get supported hash functions from your cloud provider


import argparse
import os
import subprocess
import time
import ujson as json
import logging
from datetime import datetime

import halo
from clint.textui import colored


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
        self.clone = False


class Flat():
    def __init__(self, path):
        self.path = path
        self.files = []
        self.uids = {}
        self.names = {}
        self.lower = set()

    def update(self, name, uid, time, state=THESAME):
        self.files.append(File(name, uid, time, state))
        self.names.update({name: self.files[-1]})
        self.lower.add(name.lower())

        if uid in self.uids:
            self.names[name].clone = True
            self.uids[uid].clone = True
        else:
            self.uids.update({uid: self.files[-1]})


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
        elif file.uid in old.uids and file.clone == False:
            file.moved = True
            file.state = THESAME
        else:
            file.state = CREATED

    for name, file in old.names.items():
        if name not in new.names and (file.uid not in new.uids or file.clone):
            new.update(name, file.uid, file.time, DELETED)


def prepend(name, prefix):
    new_name = name.split('/')
    new_name[-1] = prefix + new_name[-1]
    new_name = '/'.join(new_name)
    return new_name


def rename(path, name, flat):
    '''
    Renames file to be transferred (if case-conflict occurs on other side) and
    returns the new name
    '''
    new_name = name

    while CASE_INSENSATIVE and new_name.lower() in flat.lower:
        print(red('ERROR,'), 'case mismatch:', new_name + ', renaming')
        new_name = prepend(new_name, '_')

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
    uid and last modified time
    '''
    command = ['rclone', 'lsjson', '-R', '--files-only', '--hash', path]

    result = subprocess.Popen(command, stdout=subprocess.PIPE)

    list_of_dicts = json.load(result.stdout)

    out = Flat(path)
    for d in list_of_dicts:
        time = d['ModTime'][:19]
        time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S").timestamp()

        hashsize = str(d['Size'])
        hashsize += d['Hashes'][HASH_NAME]

        out.update(d['Path'], hashsize, time)

    return out


def r_sync(lcl, rmt):
    '''Recovery sync function'''
    for name, file in lcl.names.items():
        if name in rmt.names:
            if file.uid != rmt.names[name].uid:
                if file.time > rmt.names[name].time:
                    push(lcl.path + name, rmt.path + name)
                else:
                    pull(lcl.path + name, rmt.path + name)

        elif file.uid in rmt.uids and not file.clone \
                                  and not rmt.uids[uid].clone:
            if file.time > rmt.uids[file.uid].time:
                move(rmt.path + rmt.uids[file.uid].name, rmt.path + name)
            else:
                move(lcl.path + name, lcl.path + rmt.uids[file.uid].name)
        else:
            new_name = rename(lcl.path, name, rmt)
            push(lcl.path + name, rmt.path + name)

    for name, file in rmt.names.items():
        if name not in lcl.names and (file.uid not in lcl.uids or file.clone):
            new_name = rename(rmt.path, name, lcl)
            pull(lcl.path + name, rmt.path + name)


def sync(old, lcl, rmt):
    '''Normal sync function'''
    if recover:
        r_sync(lcl, rmt)
        return

    for name, file in sorted(lcl.names.items()):
        if file.state == CREATED:
            new_name = rename(lcl.path, name, rmt)
            push(lcl.path + new_name, rmt.path + new_name)

        elif name in rmt.names:
            # Neither moved or both moved to same place
            LOGIC[file.state][rmt.names[name].state](
                lcl.path + name, rmt.path + name)

        elif file.moved:
            if file.uid in rmt.uids and rmt.uids[file.uid].moved:
                # Both moved to different places
                move(lcl.path + name, lcl.path + rmt.uids[file.uid].name)
            else:
                # Only lcl moved
                move(rmt.path + old.uids[file.uid].name, rmt.path + name)
                LOGIC[THESAME][rmt.names[old.uids[file.uid].name].state](
                    lcl.path + name, rmt.path + name)

        elif old.names[name].uid in rmt.uids:
            # Only rmt has moved
            rmt_name = rmt.uids[old.names[name].uid].name

            move(lcl.path + name, lcl.path + rmt_name)
            LOGIC[file.state][THESAME](lcl.path + rmt_name, rmt.path + rmt_name)

        else:
            print(red('WARNING:'), 'fell off switch in sync function')
            logging.warning('Fell off switch in sync function with: %s', name)

    for name, file in sorted(rmt.names.items()):
        if file.state == CREATED:
            new_name = rename(rmt.path, name, lcl)
            pull(lcl.path + new_name, rmt.path + new_name)


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
            return True
        else:
            return _have(nest['fold'][chain[0]], chain[1:])

    return False


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
              ylw(' Move: ') + source + cyn(' to: ') + dest)
        logging.info('MOVE: %s TO %s', source, dest)
        subprocess.run(['rclone', 'moveto', source, dest])
    else:
        print(ylw('Move: ') + source + cyn(' to: ') + dest)


def push(source, dest):
    '''Copy source (at local) to dest (at remote)'''
    global counter, LOG
    counter += 1

    if not dry_run:
        print('%d/%d' % (counter, total_jobs) + cyn(' Push: ') + source)
        logging.info('PUSH: %s', source)
        subprocess.run(['rclone', 'copyto', source, dest])
    else:
        print(cyn("Push: ") + source)


def pull(dest, source):
    '''Copy source (at remote) to dest (at local)'''
    global counter, LOG
    counter += 1

    if not dry_run:
        print('%d/%d' % (counter, total_jobs) + mgt(' Pull: ') + source)
        logging.info('PULL: %s', source)
        subprocess.run(['rclone', 'copyto', source, dest])
    else:
        print(mgt("Pull: ") + source)


def null(*args):
    return


def conflict(source, dest):
    '''Rename and copy conflicts both ways'''

    print(red('Conflict: ') + source)

    if not dry_run:
        logging.warning('CONFLICT: %s', source)

    move(source, prepend(source, 'lcl_'))
    move(dest, prepend(dest, 'rmt_'))

    push(prepend(source, 'lcl_'), prepend(dest, 'lcl_'))
    pull(prepend(source, 'rmt_'), prepend(dest, 'rmt_'))


def delL(left, right):
    '''Delete left (at local)'''
    global counter
    counter += 1

    if not dry_run:
        print('%d/%d' % (counter, total_jobs) + ylw(' Delete: ') + left)
        logging.info('DELETE: %s', left)
        subprocess.run(['rclone', 'delete', left])
    else:
        print(ylw("Delete: ") + left)


def delR(left, right):
    '''Delete right (at remote)'''
    delL(right, left)


# ****************************************************************************
# *                           Definitions / Set-up                           *
# ****************************************************************************


print('''
Copyright 2019 C. J. Williams (CHURCHILL COLLEGE)
This is free software with ABSOLUTELY NO WARRANTY''')

CWD = os.getcwd()
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
             '1': True, "0": False, 't': True, 'true': True, 'f': False,
             'false': False, 'Y': True, 'N': False, 'Yes': True, "No": False,
             '': True}

ylw = colored.yellow   # delete/move
cyn = colored.cyan     # push
mgt = colored.magenta  # pull
red = colored.red      # error/conflict
grn = colored.green    # info

spin = halo.Halo(spinner='dots', placement='right', color='yellow')

LOGIC = [[null,      pull,       delL,   conflict],
         [push,      conflict,   push,   conflict],
         [delR,      pull,       null,   pull],
         [conflict,  conflict,   push,   conflict], ]

#Set up logging
if not os.path.exists(DRIVE_DIR + 'logs/'):
    subprocess.run(['mkdir', DRIVE_DIR + 'logs/'])

log_file = DRIVE_DIR + 'logs/' + datetime.now().strftime('%Y-%m-%d')

logging.basicConfig(filename=log_file, level=logging.DEBUG, datefmt='%H:%M:%S', 
                    format='%(asctime)s-%(levelname)s-%(message)s')

# ****************************************************************************
# *                             Parsing Arguments                            *
# ****************************************************************************


parser = argparse.ArgumentParser()

parser.add_argument("folders", help="folders to sync", nargs='*')
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
recover = args.recovery


# ****************************************************************************
# *                               Main Program                               *
# ****************************************************************************


# get the master structure
if not os.path.exists(DRIVE_DIR + 'master.json'):
    print(ylw('WARN'), '"master.json" missing, this must be your first run')
    write('master.json', empty())

master = read(DRIVE_DIR + 'master.json')

if os.path.exists(DRIVE_DIR + 'rsinc.tmp'):
    print(red('ERROR') + ', detected a crash, found rsinc.tmp')

    corrupt = read(DRIVE_DIR + 'rsinc.tmp')['folder']
    if corrupt in folders:
        folders.remove(corrupt)

    folders.insert(0, corrupt)
    recover = True
    logging.warning('Detected crash, recovering %s', corrupt)

for folder in folders:
    print('')
    path_lcl = BASE_L + folder + '/'
    path_rmt = BASE_R + folder + '/'

    min_path = get_min(master, folder)

    # Determine if first run
    if have(master, folder):
        print(grn('Have:'), qt(folder) + ', entering sync & merge mode')
    else:
        print(ylw('Don\'t have:'), qt(folder) + ', entering first_sync mode')
        recover = True

    # Scan directories
    spin.start(("Crawling: ") + qt(folder))

    lcl = lsl(path_lcl)
    rmt = lsl(path_rmt)
    old = Flat('null')

    spin.stop_and_persist(symbol='✔')

    # First run & recover mode
    if recover:
        print('Running', ylw('recover/first_sync'), 'mode')
    else:
        print('Reading last state.')
        branch = get_branch(master, folder)
        unpack(branch, old)

        calc_states(old, lcl)
        calc_states(old, rmt)

    # Main logic
    dry_run = True
    counter = 0

    print(grn('Dry pass:'))
    sync(old, lcl, rmt)

    dry_run = args.dry
    total_jobs = counter

    if dry_run:
        print('Found:', counter, 'job(s)')
    else:
        if counter == 0:
            print('Found no jobs')
        elif auto or strtobool[input('Execute? ')]:
            print(grn("Live pass:"))
            counter = 0
            
            write(DRIVE_DIR + 'rsinc.tmp', {'folder': folder})
            sync(old, lcl, rmt)

            # Merge into master and clean up
            spin.start(grn('Saving: ') + qt(min_path))

            merge(master, min_path, pack(lsl(BASE_L + min_path)))
            write(DRIVE_DIR + 'master.json', master)

            subprocess.run(["rm", DRIVE_DIR + 'rsinc.tmp'])

            spin.stop_and_persist(symbol='✔')

        if args.clean:
            spin.start(grn('Pruning: ') + qt(min_path))

            subprocess.run(["rclone", 'rmdirs', path_rmt])
            subprocess.run(["rclone", 'rmdirs', path_lcl])

            spin.stop_and_persist(symbol='✔')        

    recover = args.recovery

print('')
print(grn("All synced!"))
