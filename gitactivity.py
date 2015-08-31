#!/usr/bin/env python
#
#

import git
import click
import json
import os
import shutil
import sys
import datetime
import time

REPOS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".repos"))


class RepoSettingsRepository(object):

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def __init__(self, name, path, url, **kwargs):
        self.name = name
        self.path = path
        self.url = url

    def to_dict(self):
        return {
            "name": self.name,
            "path": self.path,
            "url": self.url,
        }


class RepoSettings(object):

    @classmethod
    def from_dict(cls, data):
        repos = []
        for repo_data in data["repos"]:
            repos.append(RepoSettingsRepository.from_dict(repo_data))
        return cls(repos)

    def __init__(self, repos=None):
        if repos is None:
            repos = []
        self.repos = repos

    def to_dict(self):
        return {
            "repos": [repo.to_dict() for repo in self.repos]
        }


def get_settings():
    try:
        with open("repos.json", "r") as f:
            return RepoSettings.from_dict(json.load(f))
    except (IOError, ValueError):
        return RepoSettings()


def save_settings(settings):
    with open("repos.json", "w") as f:
        json.dump(settings.to_dict(), f)


@click.group()
def gitactivity():
    if not os.path.exists(REPOS_DIR):
        os.makedirs(REPOS_DIR)


@gitactivity.command()
def fetch():
    settings = get_settings()
    for repo in settings.repos:
        if not os.path.exists(repo.path):
            repo = git.repo.Repo.clone_from(repo.url, repo.path)
        else:
            repo = git.repo.Repo(repo.path)

        for remote in repo.remotes:
            remote.fetch()


@gitactivity.command()
def list():
    settings = get_settings()
    for repo in settings.repos:
        print "{} from {}".format(repo.name, repo.url)


@gitactivity.command()
@click.argument("name")
@click.argument("url")
def add(name, url):
    settings = get_settings()
    path = os.path.join(REPOS_DIR, name)
    settings.repos.append(RepoSettingsRepository(name, path, url))
    save_settings(settings)


@gitactivity.command()
@click.argument("name")
def delete(name):
    settings = get_settings()
    repo_to_delete = None
    for repo in settings.repo:
        if repo.name == name:
            repo_to_delete = repo
            break
    else:
        print("Cannot delete repo with name {}".format(name))
        sys.exit(1)

    settings.repos.remove(repo_to_delete)
    shutil.rmtree(repo_to_delete.path)


@gitactivity.command()
def summarize():
    settings = get_settings()
    commits_in_range = set()
    now = datetime.datetime.now()
    for repo_meta in settings.repos:
        commits = set()
        repo = git.repo.Repo(repo_meta.path)
        for ref in repo.refs:
            for commit in repo.iter_commits(ref):
                commits.add(commit)

        for commit in sorted(commits, key=lambda c: c.authored_date):
            authored_dt = datetime.datetime.fromtimestamp(commit.authored_date)
            if now - authored_dt < datetime.timedelta(days=8):
                commits_in_range.add((repo_meta.name, commit))

    for repo, commit in sorted(commits_in_range, key=lambda (r,c): c.authored_date):
        print repo, "|", time.ctime(commit.authored_date), "|", commit.summary

if __name__ == "__main__":
    gitactivity()
