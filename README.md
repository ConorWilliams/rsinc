# Rsinc

Rsinc is a two-way cloud synchronisation client for **Linux**. Rsinc utilises [rclone](https://github.com/ncw/rclone) as its back-end while the synchronisation logic is carried out in Python. I have deliberately keep rsinc's source succinct (\~460 sloc, single script) in an attempt to make modifying rsinc to your own needs easier.

## Features

* Robust two-way syncing 
* Tracks file moves
* **Partial/selective** syncing for improved speed
* Recovery mode
* Dry-run mode 
* Crash detection and recovery
* Detailed logging
* Case checking for clouds (onedrive) that are case insensitive

## Install/Setup

Install [rclone](https://github.com/ncw/rclone) and [configure](https://rclone.org/docs/) as appropriate for your cloud service.

Install rsinc with: `pip3 install git+https://github.com/ConorWilliams/rsinc` 

Open the config file, `~/.rsinc/config.json` and modify as appropriate. It should look something like something like this:

```json {
    "BASE_L": "/home/conor/",
    "BASE_R": "onedrive:",
    "CASE_INSENSATIVE": true,
    "DEFAULT_DIRS": [
        "cpp",
        "docs",
        "cam"
    ],
    "HASH_NAME": "SHA-1"
}
```

`BASE_L` is the absolute path to the local 'root' that your remote will be synced to. `BASE_R` is the name of your rclone remote. `CASE_INSENSATIVE` is a boolian flag that controls the case checking. If both remote and local have the same case sensitivity this can be set to false else set true. `DEFAULT_DIRS` are a list of first level directories inside `BASE_L` and `BASE_R` which are synced when run with the `-D`/`--default` flags. `HASH_NAME` is the name of the hash function used to detect file changes, run `rclone lsjson --hash 'BASE_R/path_to_file'` for available hash functions. SHA-1 seems to be the most widely supported.

## Using

Run rsinc with: `rsinc 'path1 path2 etc'` where `path1`, `path2` are paths to folders that exist in both `BASE_L` and `BASE_R`. Or `cd` to a path in `BASE_L` that exists in `BASE_R` and run: `rsinc`.

Rsinc will scan the paths and print to the terminal all the actions it will take. Rsinc will then present a (y/n) input to confirm if you want to proceed with those actions.

Rsinc will detect the first run on a path and launch **recovery mode** which will make the two paths (local and remote) identical by copying any files that exist on just one side to the other and copying the newest version of any files that exist both sides to the other. It also matches moves for any files for which this can be uniquely determined (i.e. there exists only one copy of this file on each of local and remote). Recovery mode **does not delete** any files however conflicting files will be overwritten (keeping newest).

If it is not the first run on a path rsinc will perform a traditional two-way synchronisation, tracking if the files have been moved, deleted or updated then mirroring these actions. Conflicts are resolved by renaming the files and copying both ways (no data loss).  

### Command Line Arguments

The optional arguments available are:

*  -h, --help      Show help message and exit.
*  -d, --dry       Do a dry run, no changes are made at all.
*  -c, --clean     Remove any empty directories in local and remote.
*  -D, --default   Sync default folders, specified in `~/.rsinc/config.json`.
*  -r, --recovery  Force recovery mode.
*  -a, --auto      Automatically applies changes without requesting permission.
*  -p, --purge     Deletes the `~/.rsinc/master.json` file resulting in a total reset of tracking.




about logs

## Details



