# Provides interface to rclone commands

import subprocess
import ujson as json
from datetime import datetime
import logging
import os

import tqdm

from .classes import Flat, Struct
from .colors import red, mgt, cyn, ylw

log = logging.getLogger(__name__)

RCLONE_ENCODING = "UTF-8"

track = Struct()  # global used to track how many operations sync needs.


def make_dirs(dirs):
    """
    @brief      Makes new directories

    @param      dirs  List of directories to mkdir

    @return     None.
    """
    global track

    if track.pool.max_workers == 1 or len(dirs) == 0:
        return

    for d in tqdm(sorted(dirs, key=len), desc="mkdirs"):
        subprocess.run(['rclone', 'mkdir', d])

    track.pool.wait()


def prepend(name, prefix):
    """
    @brief      Prepends prefix to file name.

    @param      name    The full path to the file
    @param      prefix  The prefix to prepend to the file name

    @return     Path to file with new name.
    """
    new_name = name.split('/')
    new_name[-1] = prefix + new_name[-1]
    new_name = '/'.join(new_name)
    return new_name


def resolve_case(name, flat):
    """
    @brief      Prepends name with '_' until no case conflicts in flat.
    @param      name  The name of the file in flat
    @param      flat  The Flat with the file in
    @return     New name of the file.
    """
    global track

    new_name = name

    if track.case:
        while new_name.lower() in flat.lower:
            new_name = prepend(new_name, '_')
    else:
        while new_name in flat.names:
            new_name = prepend(new_name, '_')

    return new_name


def lsl(path, hash_name, regexs=[]):
    """
    @brief      Runs rclone lsjson and builds a Flat.

    @param      path       The path to lsjson
    @param      hash_name  The hash name to use for the file uid's
    @param      regexs     List of compiled regexes, a file path/name that
                           matches any regex will be ignored

    @return     A Flat of files representing the current state of directory at
                path.
    """
    global track

    command = ['rclone', 'lsjson', '-R', '--files-only', path]
    subprocess.run(['rclone', 'mkdir', path])
    result = subprocess.Popen(command + track.rclone_flags,
                              stdout=subprocess.PIPE)
    list_of_dicts = json.load(result.stdout)

    command = ['rclone', 'hashsum', hash_name, path]
    result = subprocess.Popen(command, stdout=subprocess.PIPE)
    hashes = {}

    for file in result.stdout:
        decode = file.decode(RCLONE_ENCODING).strip()
        tmp = decode.split('  ', 1)
        hashes[tmp[1]] = tmp[0]

    out = Flat(path)
    for d in list_of_dicts:
        if not any(r.match(d['Path']) for r in regexs):
            time = d['ModTime'][:19]
            time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S").timestamp()

            hashsize = str(d['Size'])

            hash = hashes.get(d['Path'], None)
            if hash is not None:
                hashsize += hash
            else:
                print(red('ERROR:'), "can\'t find", d['Path'], 'hash')
                continue

            out.update(d['Path'], hashsize, time)

    return out


def safe_push(name, flat_s, flat_d):
    """
    @brief      Used to push file when file not in destination, performs case
                checking / correcting and updates Flats as appropriate.

    @param      name    The name of the file to push
    @param      flat_s  The source Flat
    @param      flat_d  The destination Flat

    @return     None.
    """
    global track

    old = ''
    new = name

    pair = [flat_s, flat_d]
    c = 1

    while new != old:
        new, old = resolve_case(new, pair[c]), new
        c = 0 if c == 1 else 1

    push(name, new, flat_s, flat_d)

    cpd_dump = flat_s.names[name].dump()
    flat_d.update(new, *cpd_dump)

    if new != name:
        # Must wait for copy to finish before renaming source.
        track.pool.wait()
        move(name, new, flat_s)


def safe_move(name_s, name_d, flat_in, flat_mirror):
    """
    @brief      Moves file performing case checking / correcting.

    @param      name_s       The name of the source file
    @param      name_d       The name of the destination file
    @param      flat_in      The Flat in which the move occurs
    @param      flat_mirror  The Flat which the move is mirroring

    @return     None.
    """
    old = ''
    new = name_d

    pair = [flat_in, flat_mirror]
    c = 0

    while new != old:
        new, old = resolve_case(new, pair[c]), new
        c = 0 if c == 1 else 1

    if new != name_d:
        move(name_d, new, flat_mirror)

    move(name_s, new, flat_in)


def move(name_s, name_d, flat):
    """
    @brief      Moves file in flat. Updates flat as appropriate.

    @param      name_s  The name of the source file
    @param      name_d  The name of the destination file
    @param      flat    The Flat in which the move occurs

    @return     None.
    """
    global track
    track.count += 1

    base = flat.path

    if base == track.lcl:
        col = cyn
    elif base == track.rmt:
        col = mgt

    if os.path.split(name_s)[0] == os.path.split(name_d)[0]:
        text = 'Rename:'
    else:
        text = "Move:"

    info = col(text) + ' (%s) ' % base + name_s + col(' to: ') + name_d
    text = text.ljust(10)

    if not track.dry:
        print('%d/%d' % (track.count, track.total), info)
        log.info('%s(%s) %s TO %s', text.upper(), base, name_s, name_d)
        track.pool.run(['rclone', 'moveto', base + name_s, base + name_d] +
                       track.rclone_flags)
    else:
        print(info)

    mvd_dump = flat.names[name_s].dump()
    flat.rm(name_s)
    flat.update(name_d, *mvd_dump)


def push(name_s, name_d, flat_s, flat_d):
    """
    @brief      Copies file.

    @param      name_s  The name of the source file
    @param      name_d  The name of the destination file
    @param      flat_s  The Flat containing the source file
    @param      flat_d  The destination Flat

    @return     None.
    """
    global track
    track.count += 1

    if flat_s.path == track.lcl and flat_d.path == track.rmt:
        text = 'Push:'
        col = mgt

    elif flat_s.path == track.rmt and flat_d.path == track.lcl:
        text = 'Pull:'
        col = cyn

    info = col('%s ' % text) + name_d
    text = text.ljust(10)

    if not track.dry:
        print('%d/%d' % (track.count, track.total), info)
        log.info('%s%s', text.upper(), name_d)
        cmd = ['rclone', 'copyto', flat_s.path + name_s, flat_d.path + name_d]
        track.pool.run(cmd + track.rclone_flags)
    else:
        print(info)


def pull(name_s, name_d, flat_s, flat_d):
    push(name_d, name_s, flat_d, flat_s)


def conflict(name_s, name_d, flat_s, flat_d):
    """
    @brief      Resolves conflicts by renaming files and copying both ways.

    @param      name_s  The name of the conflicting file in flat_s
    @param      name_d  The name of the conflicting file in flat_d
    @param      flat_s  The Flat of lcl/rmt files
    @param      flat_d  The Flat of rmt/lcl files

    @return     None.
    """
    global track

    print(
        red('Conflict: ') + '%d:%d: %s' %
        (flat_s.names[name_s].state, flat_d.names[name_d].state, name_s), )

    if not track.dry:
        log.info('CONFLICT: %s', name_s)

    nn_s = resolve_case(prepend(name_s, 'lcl_'), flat_s)
    nn_d = resolve_case(prepend(name_d, 'rmt_'), flat_d)

    move(name_s, nn_s, flat_s)
    move(name_d, nn_d, flat_d)

    if nn_s != name_s or nn_d != name_d:
        # Must wait for renames before copying.
        track.pool.wait()

    safe_push(nn_s, flat_s, flat_d)
    safe_push(nn_d, flat_d, flat_s)


def delL(name_s, name_d, flat_s, flat_d):
    """
    @brief      Deletes file.

    @param      name_s  The name of the file to delete
    @param      name_d  Dummy argument
    @param      flat_s  The Flat in containing the file to delete
    @param      flat_d  Dummy argument

    @return     { description_of_the_return_value }
    """
    global track
    track.count += 1

    info = ylw('Delete: ') + flat_s.path + name_s

    if not track.dry:
        print('%d/%d' % (track.count, track.total), info)
        log.info('DELETE:   %s', flat_s.path + name_s)
        cmd = ['rclone', 'delete', flat_s.path + name_s]
        track.pool.run(cmd + track.rclone_flags)
    else:
        print(info)


def delR(name_s, name_d, flat_s, flat_d):
    delL(name_d, name_s, flat_d, flat_s)


def null(*args):
    return
