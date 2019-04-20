

import argparse
import copy
import halo
import os.path
import re
import subprocess
import sys
import time
import ujson as json

from clint.textui import colored
from datetime import datetime

HASH_ON = True


command = ['rclone', 'lsjson', '-R', '--files-only', '/home/conor/test']

if HASH_ON:
    command += ['--hash']


result = subprocess.Popen(command, stdout=subprocess.PIPE)

list_of_dicts = json.load(result.stdout)

out = {}
for d in list_of_dicts:
    time = d['ModTime'][:19]
    time = int(datetime.strptime(time, "%Y-%m-%dT%H:%M:%S").timestamp())
    time += float(d['ModTime'][19:21])

    hashsize = str(d['Size'])
    if HASH_ON:
        hashsize += d['Hashes']['SHA-1']

    out.update({d['Path']: {'time': time, 'id': hashsize}})

print('hi' == 'hi')
