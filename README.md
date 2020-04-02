# gitlab-backup

Collects all projects for one or more Gitlab groups (including subgroups) and stores them to a folder for backup.

The first time the script finds a project it gets cloned, the next time the project is just pulled to keep it up to date. 