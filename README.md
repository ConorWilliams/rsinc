# Rsinc

Rsinc is a two-way cloud synchronisation client for **Linux**. Rsinc utilises [rclone](https://github.com/ncw/rclone) as its back-end while the synchronisation logic is carried out in Python. I have deliberately keep rsinc's source succinct (\~500 sloc, single script) in an attempt to make modifying rsinc to your own needs easier.

## Features

* Robust two-way syncing 
* Tracks file moves
* **Selective** syncing for improved speed
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

Rsinc will detect the first run on a path and launch **recovery mode** which will make the two paths (local and remote) identical by copying any files that exist on just one side to the other and copying the newest version of any files that exist both sides to the other. It also matches moves for any files for which this can be unambiguously (i.e. there exists only one copy of this file on each of local and remote). Recovery mode **does not delete** any files however conflicting files will be overwritten (keeping newest).

If it is not the first run on a path rsinc will perform a traditional two-way synchronisation, tracking if the files have been moved, deleted or updated then mirroring these actions. Conflicts are resolved by renaming the files and copying both ways (no data loss).  

### Command Line Arguments

The optional arguments available are:

*  -h, --help, show help message and exit.
*  -d, --dry, do a dry run, no changes are made at all.
*  -c, --clean, remove any empty directories in local and remote.
*  -D, --default, sync default folders, specified in `~/.rsinc/config.json`.
*  -r, --recover-y, force recovery mode.
*  -a, --auto, automatically applies changes without requesting permission.
*  -p, --purge, deletes the `~/.rsinc/master.json` file resulting in a total reset of tracking.

## Details

### Two-Way Syncing

Rsinc determines, for each file in local and remote, whether they have been updated, moved, deleted, created or stayed the same. This is achieved by comparing the files in local and remote to an image of the files in local at the last run (should to be identical remote at last run). The path (unique) of the file as well as its ID (composition of a files hash and size) are used to make these comparisons. Files are tagged as 'clones' if there exists more than one file with the same ID in a directory (i.e two copies of the same file with different names).

Files tagged as created are copied to their complimentary locations. Next moves are mirrored giving preference to remote in the event of a move conflict. Rsinc checks the copies and moves do not produce a name conflict and renames first if necessary. Finally the moved and unmoved files are modified according according to:

state | remote unchanged | remote updated | remote deleted | remote created
----- | ---------------- | -------------- | -------------- |  -------------
local unchanged   | do nothing    | pull remote | delete local  | conflict
local updated     | push local    | conflict    | push local    | conflict
local deleted     | delete remote | pull        | do nothing    | pull remote
local created     | conflict      | conflict    | push local    | conflict

This allows for complex tracking such as a local moves and a remote modification being compound.

Through out rsinc clones are never moved as movements cannot be unambiguously determined.

### Recovery Mode

moves 

### Selective Syncing

### Logging

As well as printing to the terminal everything rsinc does, detailed logs are kept at `~/.rsinc/logs/` of all the actions rsinc performs.
