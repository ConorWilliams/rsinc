# Rsinc

Rsinc is a two-way cloud synchronisation client for **Linux**. Rsinc utilises [rclone](https://github.com/ncw/rclone) as its back-end while the synchronisation logic is carried out in Python. I hope rsinc's source is succinct enough (\~600 sloc across two files) to make modifying rsinc to your own needs easy.

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

Rsinc will create a `~/.rsinc/` directory and configure it with the defaults.

Open the config file, `~/.rsinc/config.json` and modify as appropriate. It should look something like something like this by default:

```json {
    "BASE_L": "/home/conor/",
    "BASE_R": "onedrive:",
    "CASE_INSENSATIVE": true,
    "DEFAULT_DIRS": [
        "cpp",
        "docs",
        "cam"
    ],
    "HASH_NAME": "SHA-1",
    "LOG_FOLDER": "/home/conor/.rsinc/logs/",
    "MASTER": "/home/conor/.rsinc/master.json",
    "TEMP_FILE": "/home/conor/.rsinc/rsinc.tmp"
}
```

- `BASE_L` is the absolute path to the local 'root' that your remote will be synced to. 
- `BASE_R` is the name of your rclone remote. 
- `CASE_INSENSATIVE` is a boolean flag that controls the case checking. If both remote and local have the same case sensitivity this can be set to false, else set true. 
- `DEFAULT_DIRS` are a list of first level directories inside `BASE_L` and `BASE_R` which are synced when run with the `-D` or `--default` flags. 
- `HASH_NAME` is the name of the hash function used to detect file changes, run `rclone lsjson --hash 'BASE_R/path_to_file'` for available hash functions. SHA-1 seems to be the most widely supported.
- `LOG_FOLDER` is the path where log files will be written to.
- `MASTER` is the file that will store data about the contents of local and remote at the last run.
- `TEMP_FILE` is a file used to detect if rsinc has crashed during a run.

## Using

Run rsinc with: `rsinc 'path1' 'path2' 'etc'` where `path1`, `path2` are paths to folders/directories in `BASE_L` or `BASE_R` that will be synced. Alternatively `cd` to a path in `BASE_L` and run: `rsinc`. If any of the paths to not exist in in either local or remote rsinc will mkdir.  

Rsinc will scan the paths and print to the terminal all the actions it will take. Rsinc will then present a (y/n) input to confirm if you want to proceed with those actions.

Rsinc will detect the first run on a path and launch **recovery mode** which will make the two paths (local and remote) identical by copying any files that exist on just one side to the other and copying the newest version of any files that exist both sides to the other. Recovery mode **does not delete** any files however, conflicting files will be overwritten (keeping newest).

If it is not the first run on a path rsinc will perform a traditional two-way synchronisation, tracking if the files have been moved, deleted or updated then mirroring these actions. Conflicts are resolved by renaming the files and then copying them both ways (no data loss).  

### Command Line Arguments

The optional arguments available are:

*  -h, --help, show help message and exit.
*  -d, --dry, do a dry run, no changes are made at all.
*  -c, --clean, remove any empty directories in local and remote.
*  -D, --default, sync default folders, specified in config file.
*  -r, --recover-y, force recovery mode.
*  -a, --auto, automatically applies changes without requesting permission.
*  -p, --purge, deletes the master file resulting in a total reset of tracking.
*  --config, enter path to a config file, defaults to `~/.rsinc/config.json`.

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

This allows for complex tracking such as - a local move and a remote modification -  being compound.

Throughout rsinc clones are only moved if the move can be unambiguously determined.

### Recovery Mode

moves 

### Selective Syncing

### Logging

As well as printing to the terminal everything rsinc does, detailed logs are kept at `~/.rsinc/logs/` of all the actions rsinc performs.
