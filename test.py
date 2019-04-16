from subprocess import PIPE, run, Popen
import re
from datetime import datetime
import time


LINE_FMT = re.compile(u'\s*([0-9]+) ([\d\-]+) ([\d:]+).([\d]+) (.*)')
TIME_FMT = '%Y-%m-%d %H:%M:%S'

command = ['rclone', 'lsl', '/home/conor/ROMS']
result = Popen(command, stdout=PIPE, universal_newlines=True)

result = result.stdout.readline

d = {}

for line in iter(result, ''):
    out = LINE_FMT.match(line)

    size = int(out.group(1))
    age = out.group(2) + ' ' + out.group(3)
    date_time = int(time.mktime(datetime.strptime(age, TIME_FMT).timetuple()))
    filename = out.group(5)

    d[filename] = {u'bytesize': size, u'datetime': date_time}

import json

with open('data.json', 'w') as fp:
    json.dump(d, fp, sort_keys=True, indent=4)

with open('data.json', 'r') as fp:
    data = json.load(fp)

for f in d:
    print(f)
