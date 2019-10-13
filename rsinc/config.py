# Provides interactive command line configure

import os
import subprocess

import ujson

from .colors import grn, red, ylw

STB = set(("y", "yes", "Y", "Yes"))

hashes = ["MD5", "SHA-1", "DropboxHash", "QuickXorHash", "Whirlpool", "CRC-32"]


def get_hashes(path):
    # Recursivly search for a file to hash in path
    print("Searching:", path)

    c1 = ["rclone", "lsjson", "--files-only", "--hash", "--copy-links", path]
    c2 = ["rclone", "lsjson", "--dirs-only", "--copy-links", path]

    r1 = subprocess.Popen(c1, stdout=subprocess.PIPE)
    r2 = subprocess.Popen(c2, stdout=subprocess.PIPE)

    files = ujson.load(r1.stdout)
    dirs = ujson.load(r2.stdout)

    if len(files) == 0:
        for d in dirs:
            tmp = get_hashes(os.path.join(path, d["Path"]))
            if tmp is not None:
                return tmp

        return None
    else:
        return set(files[0]["Hashes"].keys())


def config_cli(config_path):
    print()
    print("Starting", ylw("configuration"), "mode")

    DRIVE_DIR = os.path.dirname(config_path)  # Where config lives

    BASE_L = os.path.expanduser(input('Path to local root folder i.e "~/": '))
    BASE_L = os.path.normpath(BASE_L)
    print("Local root is:", grn(BASE_L))
    print()

    BASE_R = os.path.expanduser(
        input('Path to remote root folder i.e "onedrive:": ')
    )
    BASE_R = os.path.normpath(BASE_R)
    if BASE_R[-1] != ":":
        BASE_R += ":"
        print('Missing trailing ":" corrected to:', BASE_R)

    print("Remote root is:", grn(BASE_R))
    print()

    print("Finding a matching hash function...")
    lcl_hashes = get_hashes(BASE_L)
    rmt_hashes = get_hashes(BASE_R)
    common = lcl_hashes.intersection(rmt_hashes)

    if lcl_hashes is None or rmt_hashes is None or len(common) == 0:
        print(red("ERROR:"), "could not find a valid hash")
        hash = input("Please enter hash manually: ")
    else:
        hash = sorted(common, key=len)[0]

    print("Using common hash:", grn(hash))

    CASE_INSENSATIVE = (
        input("Do local and remote have same case sensativity? (y/n) ")
        not in STB
    )

    defult_config = {
        "BASE_R": BASE_R,
        "BASE_L": BASE_L,
        "CASE_INSENSATIVE": CASE_INSENSATIVE,
        "HASH_NAME": hash,
        "DEFAULT_DIRS": [],
        "LOG_FOLDER": os.path.join(DRIVE_DIR, "logs/"),
        "MASTER": os.path.join(DRIVE_DIR, "master.json"),
        "TEMP_FILE": os.path.join(DRIVE_DIR, "rsinc.tmp"),
    }

    with open(config_path, "w") as file:
        print("Writing config to:", config_path)
        ujson.dump(defult_config, file, sort_keys=True, indent=4)
