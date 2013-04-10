"""Example Fabric script that can build a simple web project
and uses Gitfab to release and deploy it.

Typical usage:

Create a release and add it to the release repository.

    fab release

Deploy the latest release:

    fab -H username@example.com deploy

"""

import sys

# Assuming we're in a subdirectory of the gitfab-deploy project.
sys.path.append('../')

import os
import shutil

from fabric.api import local, sudo, env, task

import gitfab

# Where the release is installed on the server
env.gitfab_install_dir = '/opt/example.com'

# Central repository for releases.
# This must be an existing repo that the local user (you) has write access to.
env.gitfab_releases_repo = 'ssh://git@bitbucket.org/vilcans/releases-demo.git'

# Which paths to include in a release.
env.gitfab_release_paths = [
    'public/',
    'nginx.conf',
]


def post_update(old_version, new_version, updated_files):
    """
    Possible statuses:
    Added (A), Copied (C), Deleted (D), Modified (M), Renamed (R),
    type (i.e. regular file, symlink, submodule, ...) changed (T),
    Unmerged (U), Unknown (X), pairing Broken (B).

    See the documentation for git diff --diff-filter.

    """

    # Restart Nginx when its configuration has changed.
    if 'nginx.conf' in updated_files:
        restart_nginx()

env.gitfab_post_update = post_update


@task
def build():
    """Create files that should be included in a release"""
    # This is an example of building before a release.
    # Here you can call external scripts like make, cake, etc.
    # or use Python code to generate the release.
    # For this example, we copy the files from static into the
    # release directory (public/) and concatenates all Javascript files.
    if os.path.exists('public'):
        shutil.rmtree('public')
    shutil.copytree('static', 'public')

    js = []
    for jsfile in ('src/module.js', 'src/main.js'):
        with open(jsfile) as stream:
            js.append(stream.read())
    os.makedirs('public/js')
    with open('public/js/all.js', 'w') as stream:
        stream.write('\n'.join(js))


# Use Gitfab's default deploy task
deploy = gitfab.deploy


@task
def release(version=None):
    """Creates and releases the current code.
    Takes an optional version string as parameter.

    """
    gitfab.check_working_dir_clean()
    build()
    gitfab.release(version)


@task
def restart_nginx():
    """Restart Nginx. Example of a task that's executed when needed."""
    sudo('kill -HUP $(cat /var/run/nginx.pid)')
