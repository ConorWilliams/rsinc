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

Install rsinc with: `pip3 install git+https://github.com/ConorWilliams/rsinc`, then open the config file: `~/.rsinc/config.json`. It should look something like something like this:
```python
if (isAwesome){
  return true
}
```

## Using

about logs

## Details

## Optional Arguments

