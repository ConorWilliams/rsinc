# Rsinc

Rsinc is a two-way cloud synchronisation client for **Linux**. Rsinc utilises [rclone](https://github.com/ncw/rclone) as its back-end while the synchronisation logic is carried out in Python. Rsinc tracks file moves and saves bandwidth. Rsinc (in normal mode) uses only file hashes and sizes to track files thus avoiding unreliable time stamps. I hope rsinc's source is succinct enough (\~800 sloc) to make modifying rsinc to your own needs easy.

## Features

* Robust two-way syncing
* Tracks file moves and performs compound move/updates
* **Selective** syncing for improved speed
* Multiprocess uploads/downloads/moves/deletes in parallel
* Recovery mode
* Dry-run mode
* Crash detection and recovery
* Automatic first run detection and resolution
* Git-like `.rignore` system supporting regular expressions for ignoring files
* Uses file hashes to track changes
* Case checking for clouds (OneDrive) that are case insensitive
* Colourful CLI
* Supports all clouds services [rclone](https://github.com/ncw/rclone) supports (Google Drive, Dropbox, One Drive + )


## Install/Setup

Install [rclone](https://github.com/ncw/rclone) and [configure](https://rclone.org/docs/) as appropriate for your cloud service.

Install rsinc with: `pip3 install git+https://github.com/ConorWilliams/rsinc@stable`

Rsinc will create a `~/.rsinc/` directory and configure it with the defaults.

Upon first run rsinc will launch the interactive configurer.

Open the config file, `~/.rsinc/config.json` and modify as appropriate. It should look something like this by default:

```json {
 {
    "BASE_L": "/home/conor/",
    "BASE_R": "onedrive:",
    "CASE_INSENSATIVE": true,
    "DEFAULT_DIRS": [
        "/home/conor/cpp",
        "/home/conor/docs",
        "/home/conor/cam",
        "/home/conor/py"
    ],
    "HASH_NAME": "SHA-1",
    "LOG_FOLDER": "/home/conor/.rsinc/logs/",
    "MASTER": "/home/conor/.rsinc/master.json",
    "TEMP_FILE": "/home/conor/.rsinc/rsinc.tmp"
}
```

- `BASE_L` is the absolute path to the local 'root' that your remote will be synced to.
- `BASE_R` is the name of your rclone remote. Note `BASE_R` **_should_** include the trailing colon.
- `CASE_INSENSATIVE` is a boolean flag that controls the case checking. If both remote and local have the same case sensitivity this can be set to false, else set true.
- `DEFAULT_DIRS` are a list of first level directories inside `BASE_L` and `BASE_R` which are synced when run with the `-D` or `--default` flags.
- `HASH_NAME` is the name of the hash function used to detect file changes, run `rclone lsjson --hash 'BASE_R/path_to_file'` for available hash functions. SHA-1 seems to be the most widely supported. The interactive configurer should set this automatically.
- `LOG_FOLDER` is the path where log files will be written to.
- `MASTER` is the file that will store an image of the local files at the last run, a history of previously synced directories and paths to .rignore files.
- `TEMP_FILE` is a file used to detect if rsinc has crashed during a run.

## Using

Run rsinc with: `rsinc 'path1' 'path2' 'path3' 'etc'` where `path1`, `path2` are (relative) paths to folders/directories in `BASE_L` or `BASE_R` to synced. Alternatively type a full path starting with a `/` (i.e `~/some/path/here`) and rsinc will not convert it to a relative path. If any of the paths do not exist in either local or remote rsinc will mkdir. If no paths are supplied then the current working directory will be synced. For example running `rsinc ~/Documents` will syncronise `~/Documents` to `onedrive:Documents` assuming `BASE_L = ~/` and `BASE_R = onedrive:`.  

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
*  -p, --purge, deletes the master file resulting in a **total reset** of all tracking.
*  -i, --ignore, find `.rignore` files and add them to the ignore list. Flag must be set to find new `.rignore` files.
*  --congig, launch the interactive configurer.
*  --config_path, enter path to a config file, defaults to `~/.rsinc/config.json`.

Any remaining arguments/flags will be passed through to all rclone commands rsinc calls. Note a path must be supplied to rsinc when supplying additional flags instead of relying on the implicit current working directory (which can be explicitly called with `.`).

## Details

### Two-Way Syncing

Rsinc determines, for each file in local and remote, whether they have been updated, moved, deleted, created or stayed the same. This is achieved by comparing the files in local and remote to an image of the files in local after the last run (local should be identical remote after last run). The path (unique) of the file as well as its ID (composition of a files hash and size) are used to make these comparisons. Files are tagged as 'clones' if there exists more than one file with the same ID in a directory (i.e two copies of the same file with different names).

Files tagged as 'created' are copied to their complimentary locations. Next moves are mirrored giving preference to remote in the event of a move conflict. Rsinc checks the copies and moves do not produce a name conflict and renames first if necessary. Finally the moved and unmoved files are modified according according to:

state | remote unchanged | remote updated | remote deleted | remote created
----- | ---------------- | -------------- | -------------- |  -------------
local unchanged   | do nothing    | pull remote | delete local  | conflict
local updated     | push local    | conflict    | push local    | conflict
local deleted     | delete remote | pull        | do nothing    | pull remote
local created     | conflict      | conflict    | push local    | conflict

This allows for complex tracking such as, a local move and a remote modification, being compound.

Throughout rsinc 'clones' are only moved if the move can be unambiguously determined. Moving a clone will trigger a delete and copy operation instead of a move operation for the same reason.

### Recovery Mode

In recovery mode rsinc will make local and remote identical by copying any files missing on either side to their complimentary location. If two files exist on both sides and do not have the same ID (i.e they are different) rsinc will overwrite the oldest file with the newer one.

### Selective Syncing

Rsinc stores an image of the last state in a tree structured dictionary called `nest`, this enables selective syncing. i.e syncing all the files in `dir1/dir2` but leaving all the other files in `dir1` un-synced. This is achieved by syncing `dir1/dir2` then merging the new state of `dir1/dir2` into a branch of `nest` without altering `nest`s memory of all the other files/folders in `dir1`. This means when syncing sub folders, rsinc minimises the work `rclone lsjson` does. This is important as `rclone lsjson` is the speed bottle neck of syncing.

### .rignore

Running rsinc with the `-i` flag will trigger a recursive search through `BASE_L` finding (and saving) any `.rignore` files. Within an `.rignore` file you can specify regular expressions to ignore files within the `.rignores`'s directory (and all sub directories). For example for `~/path/.rignore`:

* `.*\.txt` - recursively ignore all text file in `~/path/`.
* `\.git/` - ignore all files in `~/path/.git/`.
* `.*\.git/` - recursively ignore all files in `~/path/` inside any `.git/` folder.
* `[^/]*\.txt` - ignore any text file in `~/path/` but not in sub directories.
* `(?!.*\.py$)` - recursively ignore everything in `~/path/` unless it ends with `.py` i.e. is a python source file.

If any of the regular expressions match a files path it will be ignored. If you make a new `.rignore` file (but not if you update one) you will need to run rsinc with the `-i` flag to fetch new ignore files. It is more efficient to selectively sync the folders you want syncing than to run rsinc on a higher level directory with many ignores.

### Logging

As well as printing to the terminal everything rsinc does, logs are kept at `~/.rsinc/logs/` of all the actions rsinc performs.
