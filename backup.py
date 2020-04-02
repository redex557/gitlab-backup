#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import gitlab
import os
import coloredlogs
import logging
import shutil
from collections import namedtuple
import argparse
import re


urls = []
project_count = 0
new_count = 0
update_count = 0
empty_count = 0
subgroup_count = 0
group_count = 0
uptodate_count = 0

gl = gitlab.Gitlab.from_config('somewhere', ['python-gitlab.cfg'])

parser = argparse.ArgumentParser(description="Gitlab Group Backup Script")
parser.add_argument('-v', '--verbose', action="store_true", default=False, help="verbose mode, all output enabled")
parser.add_argument('-q', '--quite', action="store_true", default=False, help="quite mode, no output except errors")
parser.add_argument('-r', '--report', action="store_true", default=False, help="output report after backup is finished")
parser.add_argument('-d', '--directory', action='store', type=str, default='.',
                    help="directory to save the backups in, default is folder you are currently in")
parser.add_argument(dest='group_ids', type=int, nargs='+', default=[],
                    help="Groups IDs to parse for Repositorys")
args = parser.parse_args()


logger = logging.getLogger(__name__)
level = "INFO"
if args.verbose:
    level = 1
if args.quite:
    level = "WARNING"
coloredlogs.install(level=level, logger=logger, fmt="[%(asctime)s] %(message)s")

# making sure git language is set to english for parsing
my_env = os.environ.copy()
my_env["LANG"] = "en_US.UTF-8"
my_env["LC_ALL"] = "en_US.UTF-8"
my_env["LANGUAGE"] = "en_US.UTF-8"


def check_args():
    if args.verbose & args.quite:
        logger.fatal("-q and -v are not working at the same time, think about it again ;)")
        exit(-1)
    if args.directory == '.':
        logger.debug("Directory parameter not set, using folder you are currently in")
    elif not os.path.isdir(args.directory):
        logger.fatal(args.directory+" is not a valid directory")
        exit(-1)


def print_report():
    print("Done. Found %s projects in %s groups (%s subgroups)." % (project_count,group_count,subgroup_count))
    print("%s Projects where new, %s got updated, %s where up to date, %s where empty Projects" % (new_count, update_count, uptodate_count, empty_count))


def is_empty_proj(dr, n):#
    global empty_count
    try:
        onlygit = (os.listdir(dr + "/" + n) == ['.git'])
    except FileNotFoundError as e:
        logger.error(e)
        onlygit = -1
    if onlygit:
        logger.warning("Project %s is empty, deleting the folder for now." % n)
        shutil.rmtree(args.directory + "/" + n, ignore_errors=True)
        empty_count += 1
    return onlygit


def git_clone(link):
    logger.debug("git clone %s %s/%s" % (link, args.directory, name))
    process = subprocess.Popen(['git', 'clone', link, args.directory + "/" + name], env=my_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return namedtuple('Std', 'out, err')(process.stdout.read(), process.stderr.read())


def git_pull():
    process = subprocess.Popen(['git', 'pull'], cwd=args.directory + "/" + name, env=my_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return namedtuple('Std', 'out, err')(process.stdout.read(), process.stderr.read())


def proc_output(output, error, name):
    global uptodate_count, update_count
    if output:
        for s in out.decode("utf-8").split("\n"):
            if s != "":
                logger.debug(name+":  "+s)
                if re.search(r'(date)', s):
                    uptodate_count += 1
    if error:
        for s in err.decode("utf-8").split("\n"):
            if s != "":
                logger.error(name+":  "+s)
                if re.search(r'( -> )', s):
                    uptodate_count -= 1 # outputs "up to date" too
                    update_count += 1


if __name__ == '__main__':
    check_args()
    for group_id in args.group_ids:
        group_count += 1
        group = gl.groups.get(group_id)
        logger.debug('Searching in Group: ' + group.path)

        subgroups = group.subgroups.list()

        projects = group.projects.list()

        for project in projects:
            logger.debug('Found Projects:  ' + project.ssh_url_to_repo)
            urls.append((project.ssh_url_to_repo, group.path + ":" + project.path))

        for subgroup in subgroups:
            logger.debug('Searching in Subgroup: ' + subgroup.path)
            sgroup = gl.groups.get(subgroup.id)
            projects = sgroup.projects.list()
            subgroup_count += 1
            for project in projects:
                logger.debug('Found Projects:  ' + project.ssh_url_to_repo)
                urls.append((project.ssh_url_to_repo, group.path + ":" + subgroup.path + ":" + project.path))

    # Clone them all to the directory args.directory

    for url, name in urls:
        project_count += 1
        if os.path.isdir(args.directory + "/" + name):
            if not is_empty_proj(args.directory, name):
                out, err = git_pull()
                proc_output(out,err,name)
        else:
            new_count += 1
            out, err = git_clone(url)
            proc_output(out, err, name)
            is_empty_proj(args.directory, name)

    if args.report:
        print_report()
