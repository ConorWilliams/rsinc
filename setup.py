# -*- coding: utf-8 -*-
"""
Rsinc setup script for pip to install rsinc as a package.
Additionally sets up the ~/.rsinc folder and default config file.
"""

import setuptools
import os
import subprocess

import rsinc

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rsinc",
    version=rsinc.__version__,
    author=rsinc.__author__,
    author_email="conorwilliams@outlook.com",
    description="A tiny, hackable, two-way cloud synchronisation client for Linux",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ConorWilliams/rsinc",
    packages=setuptools.find_packages(),
    install_requires=[
        "ujson",
        "clint",
        "halo",
        "tqdm",
        "pyfiglet",
        "tonyg-rfc3339",
    ],
    entry_points={"console_scripts": ["rsinc=rsinc.rsinc:main"]},
    python_requires=">=3",
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Unix",
    ],
)

DRIVE_DIR = os.path.expanduser("~/.rsinc/")  # Where config and data files live

if not os.path.exists(DRIVE_DIR):
    subprocess.run(["mkdir", DRIVE_DIR])

if not os.path.exists(DRIVE_DIR + "logs/"):
    subprocess.run(["mkdir", DRIVE_DIR + "logs/"])
