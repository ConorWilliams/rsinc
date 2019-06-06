#!/usr/bin/env python3

import setuptools
import os
import json
import subprocess

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rsinc",
    version="1.0",
    author="ConorWilliams",
    author_email="conorwilliams@outlook.com",
    description="A tiny, hackable, two-way cloud synchronisation client for rclone",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ConorWilliams/rsinc",
    packages=setuptools.find_packages(),
    scripts=['bin/rsinc'],
    install_requires=['halo', 'clint'],
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Unix",
    ],
)

DRIVE_DIR = '~/.rsinc/'  # Where config and data files live
DRIVE_DIR = os.path.expanduser(DRIVE_DIR)

defult_config = {'BASE_R': 'onedrive:',
                 'BASE_L': '/home/conor/',
                 'CASE_INSENSATIVE': True,
                 'HASH_NAME': 'SHA-1',
                 "DEFAULT_DIRS": ["cpp", "docs", "cam"], }

if not os.path.exists(DRIVE_DIR):
    subprocess.run(['mkdir', DRIVE_DIR])

if not os.path.exists(DRIVE_DIR + 'logs/'):
    subprocess.run(['mkdir', DRIVE_DIR + 'logs/'])

if not os.path.exists(DRIVE_DIR + 'config.json'):
    with open(DRIVE_DIR + 'config.json', 'w') as file:
        json.dump(defult_config, file, sort_keys=True, indent=4)
