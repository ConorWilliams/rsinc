# -*- coding: utf-8 -*-
'''
Rsinc setup script for pip to install rsinc as a package.
Additionally sets up the ~/.rsinc folder and default config file.
'''

import setuptools
import os
import json
import subprocess

import rsinc

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rsinc",
    version=rsinc.__version__,
    author=rsinc.__author__,
    author_email="conorwilliams@outlook.com",
    description=
    "A tiny, hackable, two-way cloud synchronisation client for Linux",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ConorWilliams/rsinc",
    packages=setuptools.find_packages(),
    install_requires=['ujson', 'clint', 'halo', 'tqdm'],
    entry_points={
        'console_scripts': [
            'rsinc=rsinc.__main__:main',
        ],
    },
    python_requires='>=3',
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Unix",
    ],
)

DRIVE_DIR = os.path.expanduser('~/.rsinc/')  # Where config and data files live

defult_config = {
    'BASE_R':
    'onedrive:',
    'BASE_L':
    os.path.expanduser('~/'),
    'CASE_INSENSATIVE':
    True,
    'HASH_NAME':
    'SHA-1',
    'DEFAULT_DIRS': [
        os.path.expanduser("~/cpp"),
        os.path.expanduser("~/docs"),
        os.path.expanduser("~/cam"),
        os.path.expanduser("~/py"),
    ],
    'LOG_FOLDER':
    DRIVE_DIR + 'logs/',
    'MASTER':
    DRIVE_DIR + 'master.json',
    'TEMP_FILE':
    DRIVE_DIR + 'rsinc.tmp',
}

if not os.path.exists(DRIVE_DIR):
    subprocess.run(['mkdir', DRIVE_DIR])

if not os.path.exists(DRIVE_DIR + 'logs/'):
    subprocess.run(['mkdir', DRIVE_DIR + 'logs/'])

if not os.path.exists(DRIVE_DIR + 'config.json'):
    with open(DRIVE_DIR + 'config.json', 'w') as file:
        json.dump(defult_config, file, sort_keys=True, indent=4)
