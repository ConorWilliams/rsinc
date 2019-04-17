#!/usr/bin/python3

'''
merge

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

drive_dir = '/home/conor/drive/'  # where config and data files will be stored

import argparse
import json
import os.path
import re
import subprocess
import sys
import time

from clint.textui import colored
from datetime import datetime

sys.path.insert(0, drive_dir)
os.chdir(drive_dir)
import spinner
from config import *

print('''/*
 * Copyright 2019 C. J. Williams (CHURCHILL COLLEGE)
 * This is free software with ABSOLUTELY NO WARRANTY
 */''')


LINE_FMT = re.compile(u'\s*([0-9]+) ([\d\-]+) ([\d:]+).([\d]+) (.*)')
TIME_FMT = '%Y-%m-%d %H:%M:%S'

strtobool = {'yes': True, 'ye': True, 'y': True, 'n': False, 'no': False,
             1: 'yes', 0: 'no', 't': True, 'true': True, 'f': False,
             'false': False, 'Y': True, 'N': False, 'Yes': True, "No": False,
             '': True}

counter = 0
total_jobs = 0

ylw = colored.yellow  # delete
cyn = colored.cyan  # push
mgt = colored.magenta  # pull
red = colored.red  # error/conflict

grn = colored.green  # normal info

swap = str.maketrans("/", '_')


class data():
    def __init__(self, base, arg, last):
        self.path = base + arg + '/'
        self.p_old = arg.translate(swap) + last + '.json'  # remove / from arg
        self.p_tmp = arg.translate(swap) + last + '.tmp.json'  # ^

        self.d_old = {}
        self.d_tmp = {}
        self.d_dif = {}

        self.s_old = set({})
        self.s_tmp = set({})
        self.s_dif = set({})

        self.s_low = set({})

    def build_dif(self):
        self.s_old = set(self.d_old)
        self.s_tmp = set(self.d_tmp)
        self.s_low = set(k.lower() for k in self.s_tmp)

        deleted = self.s_old.difference(self.s_tmp)
        created = self.s_tmp.difference(self.s_old)

        inter = self.s_tmp.intersection(self.s_old)

        for key in created:
            self.d_dif.update({key: 3})

        for key in deleted:
            self.d_dif.update({key: 2})

        for key in inter:
            if self.d_old[key]['bytesize'] != self.d_tmp[key]['bytesize']:
                self.d_dif.update({key: 1})
            elif self.d_tmp[key]['datetime'] > self.d_old[key]['datetime']:
                self.d_dif.update({key: 1})
            else:
                self.d_dif.update({key: 0})

        self.s_dif = set(self.d_dif)


class direct():
    def __init__(self, arg):
        self.lcl = data(base_l, arg, '_lcl')
        self.rmt = data(base_r, arg, '_rmt')
        self.path = arg

    def build_dif(self):
        self.lcl.build_dif()
        self.rmt.build_dif()


def log(*args):
    if verbosity:
        print(*args)


def read(file):
    '''
    Reads json do dict and returns dict
    '''
    log('Reading', file)
    with open(file, 'r') as fp:
        d = json.load(fp)

    return d


def write(file, d):
    '''
    Writes dict to json
    '''
    if dry_run:
        return
    else:
        log('Writing', file)
        with open(file, 'w') as fp:
            json.dump(d, fp, sort_keys=True, indent=4)


def lsl(path):
    '''
    Runs rclone lsl on path and returns a dict containing each file with the
    size and last modified time as integers
    '''
    command = ['rclone', 'lsl', path]
    result = subprocess.Popen(
        command, stdout=subprocess.PIPE, universal_newlines=True)

    d = {}

    for line in iter(result.stdout.readline, ''):
        g = LINE_FMT.match(line)

        size = int(g.group(1))
        age = g.group(2) + ' ' + g.group(3)
        date_time = int(time.mktime(
            datetime.strptime(age, TIME_FMT).timetuple()))

        filename = g.group(5)

        d[filename] = {u'bytesize': size, u'datetime': date_time}

    return d


def check_exist(path):
    if os.path.exists(path):
        log('Checked', path)
        return 0
    else:
        return 1


def cpyR(source, dest):
    global counter
    counter += 1

    if not dry_run:
        print('%d/%d' % (counter, total_jobs) + cyn(' Push: ') + source)
        subprocess.run(['rclone', 'copyto', source, dest])
    else:
        print(cyn("Push: ") + source)
    return


def cpyL(dest, source):
    global counter
    counter += 1

    if not dry_run:
        print('%d/%d' % (counter, total_jobs) + mgt(' Pull: ') + source)
        subprocess.run(['rclone', 'copyto', source, dest])
    else:
        print(mgt("Pull: ") + source)
    return


def null(*args):
    return


def conflict(source, dest):
    if skip:
        print(red('Skip conflict: ') + source)
        return
    print(red('Conflict: ') + source)
    if not dry_run:
        subprocess.run(['rclone', 'moveto', source, source + ".lcl_conflict"])
        subprocess.run(['rclone', 'moveto', dest, dest + ".rmt_conflict"])

        cpyR(source + ".lcl_conflict", dest + ".lcl_conflict")
        cpyL(source + ".rmt_conflict", dest + ".rmt_conflict")
    return


def delL(left, right):
    global counter
    counter += 1

    if not dry_run:
        print('%d/%d' % (counter, total_jobs) + ylw(' Delete: ') + left)
        subprocess.run(['rclone', 'delete', left])
    else:
        print(cyn("Delete: ") + left)
    return


def delR(left, right):
    global counter
    counter += 1

    if not dry_run:
        print('%d/%d' % (counter, total_jobs) + ylw(' Delete: ') + right)
        subprocess.run(['rclone', 'delete', right])
    else:
        print(cyn("Delete: ") + right)
    return


LOGIC = [[null, cpyL, delL, conflict],
         [cpyR, conflict, cpyR, conflict],
         [delR, cpyL, null, cpyL],
         [conflict, conflict, cpyR, conflict]]

folders = []
main = []

verbosity = False

# read terminal arguments

parser = argparse.ArgumentParser()

parser.add_argument("folders", help="folders to sync", nargs='*')
parser.add_argument("-f", "--first", help="first sync flag",
                    action="store_true")
parser.add_argument(
    "-a", "--auto", help="don't ask permission", action="store_true")
parser.add_argument("-v", "--verbose", action="store_true", help="lots of info")
parser.add_argument("-s", "--skip", action="store_true", help="skip conflicts")
parser.add_argument("-d", "--dry", action="store_true", help="do a dry run")
parser.add_argument("-r", "--recovery", action="store_true",
                    help="enter recovery mode")

args = parser.parse_args()

if args.folders == []:
    folders = default_folders
else:
    for folder in args.folders:
        folders.append(folder)

dry_run = args.dry
verbosity = args.verbose
recover = args.recovery
auto = args.auto
skip = args.skip

# Build main data structure
for f in folders:
    main.append(direct(f))

# Check exists local directories, remove if not
if not args.first:
    main[:] = [tup for tup in main if not check_exist(tup.lcl.path)]


for f in main:
    print('\n')

    if check_exist(f.lcl.p_tmp) == 0 or check_exist(f.rmt.p_tmp) == 0:
        print(red('ERROR') + ', detected crash, found ' + f.path + '.tmp')
        recover = True

    # make and read files
    print(grn("Indexing: ") + f.path + ' ', end='')
    spin = spinner.Spinner()
    spin.start()

    f.lcl.d_tmp = lsl(f.lcl.path)
    f.rmt.d_tmp = lsl(f.rmt.path)

    write(f.lcl.p_tmp, f.lcl.d_tmp)
    write(f.rmt.p_tmp, f.lcl.d_tmp)

    spin.stop()
    print('')

    # First run
    if args.first:
        print("First run, making index files")

        f.lcl.d_old = f.lcl.d_tmp
        f.rmt.d_old = f.rmt.d_tmp

        write(f.lcl.p_old, f.lcl.d_old)
        write(f.rmt.p_old, f.lcl.d_old)

        recover = True
    else:
        print('Reading last state')

        if check_exist(f.lcl.p_old) or check_exist(f.rmt.p_old):
            print(red("ERROR") + " can't find old file, run with -f")
            continue

        f.lcl.d_old = read(f.lcl.p_old)
        f.rmt.d_old = read(f.rmt.p_old)

        # Confirm old dicts match
        if not recover:
            lcl = set(f.lcl.d_old)
            rmt = set(f.rmt.d_old)

            if len(lcl ^ rmt) > 0:
                print(red("ERROR") + " old dicts corrupt, size wrong")

                print("Errors at:", lcl ^ rmt)

                lcl = set(k.lower() for k in lcl)
                rmt = set(k.lower() for k in rmt)

                if len(lcl ^ rmt) == 0 and CASE_INSENSATIVE:
                    print('Detected: ' + red('CaSE ErrOrs!'))

                continue

            for item in f.lcl.d_old.values():
                if item['bytesize'] != item['bytesize'] or item['datetime'] != item['datetime']:
                    print(red("ERROR") + " old dicts corrupt at:" + key)
                    continue

    print('Finding Changes')

    f.build_dif()

    # main logic
    rmt_dif = f.rmt.s_dif.difference(f.lcl.s_dif)  # in rmt only
    lcl_dif = f.lcl.s_dif.difference(f.rmt.s_dif)  # in lcl only
    inter = f.rmt.s_dif.intersection(f.lcl.s_dif)  # in both

    mem_dry = dry_run

    for state in [True, False]:
        if state:
            print(grn('Dry pass:'))
            dry_run = True
        else:
            if not mem_dry:
                dry_run = False
            else:
                dry_run = True

            total_jobs = counter

            if counter == 0:
                print('Nothing to Sync')
                continue
            elif mem_dry:
                continue
            elif not auto and not strtobool[input('Execute? ')]:
                continue

            print(grn("Live pass:"))

        counter = 0

        for key in sorted(lcl_dif):
            if f.lcl.d_dif[key] != 2:
                if CASE_INSENSATIVE and key.lower() in f.rmt.s_low:
                    print(red('ERROR,') + ' case mismatch: ' + key)
                    print(red('NOT,') + ' pushing: ' + key)
                else:
                    cpyR(f.lcl.path + key, f.rmt.path + key)

        for key in sorted(rmt_dif):
            if f.rmt.d_dif[key] != 2:
                if CASE_INSENSATIVE and key.lower() in f.lcl.s_low:
                    print(red('ERROR,') + ' case mismatch: ' + key)
                    print(red('NOT:') + ' pulling: ' + key)
                else:
                    cpyL(f.lcl.path + key, f.rmt.path + key)

        if recover:
            for key in sorted(inter):
                if f.lcl.d_tmp[key]['bytesize'] != f.rmt.d_tmp[key]['bytesize']:
                    if f.lcl.d_tmp[key]['datetime'] > f.rmt.d_tmp[key]['datetime']:
                        cpyR(f.lcl.path + key, f.rmt.path + key)
                    elif f.lcl.d_tmp[key]['datetime'] < f.rmt.d_tmp[key]['datetime']:
                        cpyL(f.lcl.path + key, f.rmt.path + key)
        else:
            for key in sorted(inter):
                LOGIC[f.lcl.d_dif[key]][f.rmt.d_dif[key]](
                    f.lcl.path + key, f.rmt.path + key)

    dry_run = mem_dry

    print(grn('Saving: ') + f.path + ' state ', end='')
    spin = spinner.Spinner()
    spin.start()

    # clean up temps
    write(f.rmt.p_old, lsl(f.rmt.path))
    write(f.lcl.p_old, lsl(f.lcl.path))

    if not dry_run:
        subprocess.run(["rm", f.lcl.p_tmp])
        subprocess.run(["rm", f.rmt.p_tmp])

    spin.stop()
    print('')

print('')
print(grn("All Done!"))
