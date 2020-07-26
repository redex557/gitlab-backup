# gitlab-backup

Collects all projects for your account and/or any Gitlab groups (including recursive subgroups) and stores them to a folder for backup. 

The first time the script finds a project it gets cloned, the next time the project is just pulled to keep it up to date. 

# Usage

* Get all requirements using pip: 
    ```
    sudo pip install -r requirements.txt
    ```

* Setup a personal access token on your gitlab account. 
https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html

* Enter your token into "python-gitlab.cfg".

* Change server url if you host a private gitlab server.

## Run (using cronjob)

```
usage: backup.py [-h] [-v] [-q] [-r] [-d DIRECTORY] [-g GROUP_IDS [GROUP_IDS ...]] [-p] [-t]

Gitlab Backup Script

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose mode, all output enabled
  -q, --quite           Quite mode, no output except errors
  -r, --report          Output report after backup is finished
  -d DIRECTORY, --directory DIRECTORY
                        Directory to save the backups in, default is folder you are currently in
  -g GROUP_IDS [GROUP_IDS ...], --groups GROUP_IDS [GROUP_IDS ...]
                        One or more groups IDs to parse for repositorys
  -p, --personal        Enable downloading personal projects of account used.
  -t, --test            Test mode / dry run. Just collect all projects but don't download anything.
```