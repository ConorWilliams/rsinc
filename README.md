# rclone_two_way_sync
Tiny rclone two-way sync client written in python for use on Linux

Run with -h to get help

Run with --dry to do a dry run (no copy, delete or write)

Make sure rclone is installed and working first

Most things can be fixed running in recovery mode -r

Just edit the few variable at the top of sinc as appropriate for your system then run sinc on the directories you want to synchronise. If you make sinc exacutable and put in /usr/local/bin you can just run sinc inside a directory and it will sinc that directory as appropriate.

Supports partial synchronisation of directories. i.e. you can sync just /di1/dir2/ even if you have previously synced just /dir1/ and all will be automatically kept up to date so that if you sync /dir1/ in the future without any conflicts.