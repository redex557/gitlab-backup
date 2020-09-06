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
groupStr = ""

gl = gitlab.Gitlab.from_config('somewhere', ['python-gitlab.cfg'])

parser = argparse.ArgumentParser(description="Gitlab Backup Script")
parser.add_argument('-v', '--verbose', action="store_true", default=False, help="Verbose mode, all output enabled")
parser.add_argument('-q', '--quite', action="store_true", default=False, help="Quite mode, no output except errors")
parser.add_argument('-r', '--report', action="store_true", default=False, help="Output report after backup is finished")
parser.add_argument('-d', '--directory', action='store', type=str, default='.',
                    help="Directory to save the backups in, default is folder you are currently in")
parser.add_argument('-g', '--groups',dest='group_ids', type=int, nargs='+', default=[],
                    help="One or more groups IDs to parse for repositorys")
parser.add_argument('-p', '--personal',action="store_true", default=False, help="Enable downloading personal projects of account used.")
parser.add_argument('-t', '--test',action="store_true", default=False, help="Test mode / dry run. Just collect all projects but don't download anything.")

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
    logger.debug("Checking your arguments....")
    if args.verbose & args.quite:
        logger.fatal("-q and -v are not working at the same time, think about it again ;)")
        exit(1)
    if args.directory == '.':
        logger.debug("Directory parameter not set, using folder you are currently in")
    elif not os.path.isdir(args.directory):
        logger.info(args.directory+" is not a existing directory, creating it now.")
        os.makedirs(args.directory, exist_ok=True)
    if (len(args.group_ids)) == 0 and not args.personal:
        logger.fatal("No projects to download. Please  use -g/--groups or -p/--personal.")
        exit(3)
    logger.debug("Done checking your arguments.")

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


def recursive_group_search(gid, level, path=""):
    global group_count, urls, subgroup_count
    groupStr = "sub-"*level
    groupStr += "group"
    
    if level == 0:
        group_count += 1
    else:
        subgroup_count += 1

    group = gl.groups.get(gid, include_subgroups=True)
    path += group.path + ":"

    logger.debug("Searching in "+groupStr+": " + path)

    projects = group.projects.list(all=True)
    for project in projects:
        logger.debug('Found projects:  ' + project.ssh_url_to_repo)
        if not (project.ssh_url_to_repo in [i[0] for i in urls]):
            urls.append((project.ssh_url_to_repo, path + project.path))
        else: 
            logger.debug("Project already in list, skipping.")


    subgroups = group.subgroups.list(all=True)
    for subgroup in subgroups:
        recursive_group_search(subgroup.id, level+1, path=path)


if __name__ == '__main__':
    check_args()

    if args.personal:
        logger.debug("Searching for personal projects on your account...")
        projects = gl.projects.list(owned=True,all=True)
        for project in projects:
            logger.debug('Found personal projects:  ' + project.ssh_url_to_repo)
            if not (project.ssh_url_to_repo in [i[0] for i in urls]):
                urls.append((project.ssh_url_to_repo, project.path))
        logger.debug("Done searching for personal projects on your account.")


    for group_id in args.group_ids:
        logger.debug("Searching for group with ID "+str(group_id)+"...")
        recursive_group_search(group_id,0)

    # Clone them all to the directory args.directory

    if not args.test:
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
