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
}```

`BASE_L` is the absolute path to the local 'root' that your remote will be synced to. `BASE_R` is the name of your rclone remote. `CASE_INSENSATIVE` 


## Using

about logs

## Details

## Optional Arguments

