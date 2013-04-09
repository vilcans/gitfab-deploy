import os

from fabric.api import task, local, run, abort, sudo, env
from fabric.operations import prompt
from fabric.decorators import hosts
from fabric.context_managers import prefix, cd, settings, hide
from fabric.colors import green, yellow
from fabric.contrib.files import exists


def check_working_dir_clean():
    """Aborts if not everything has been committed."""
    # Inspiration:
    # http://stackoverflow.com/questions/5139290/how-to-check-if-theres-nothing-to-be-committed-in-the-current-branch

    abort_if_not_clean = env.get('gitfab_clean', 'true') == 'true'

    def failed(message):
        if abort_if_not_clean:
            abort(message + ' Use fab --set=gitfab_clean=false to ignore.')
        else:
            print yellow(message)

    with settings(warn_only=True):
        if not local('git diff --stat --exit-code').succeeded:
            failed('You have unstaged changes')
        if not local('git diff --cached --stat --exit-code').succeeded:
            failed('Your index contains uncommitted changes')

        r = local(
            'git ls-files --other --exclude-standard --directory',
            capture=True
        )
        if r != '':
            failed('Untracked files exist.')


def get_hash():
    """Get the Git hash for the current version."""
    return local('git rev-parse --short HEAD', capture=True)


def get_release_paths():
    """Get the list of paths to include in a release."""
    return env.gitfab_release_paths


def get_next_version_number():
    """Gets the latest version number and increases it by one.
    If the release repo has no version.txt file,
    assumes the version is 0.0.1

    """
    with settings(warn_only=True):
        version = releases_git('show origin/master:version.txt', capture=True)
        if version:
            version = next_version(version.strip())
        else:
            version = '0.0.1'
            print(yellow(
                'Releases repo has no version.txt: using ' + version
            ))
    return version


def releases_git(command, **kwargs):
    return local(
        'git --work-tree=. --git-dir=releases.git ' + command,
        **kwargs
    )


@task
def release(version=None):
    """Creates and releases the current code.
    Takes an optional version string as parameter.

    """
    check_working_dir_clean()

    if not os.path.exists('releases.git'):
        clone_releases_repo()

    releases_git('fetch')

    # fast-forward
    with settings(warn_only=True):
        result = releases_git('reset --mixed origin/master --')
        if not result.succeeded:
            print(yellow('Could not reset to origin/master - '
                'assuming this is the first release'))

    if not version:
        version = get_next_version_number()

    commit = get_hash()

    tag = 'v' + version
    if releases_git('tag -l ' + tag, capture=True):
        abort('Tag %s already exists in releases repo' % tag)
    if local('git tag -l ' + tag, capture=True):
        abort('Tag %s already exists in local repo' % tag)

    set_version_number(version)
    releases_git('add -fA version.txt %s' % (
        ' '.join(repr(r) for r in get_release_paths())
    ))
    message = 'Version %s, commit %s' % (version, commit)
    releases_git('diff --staged --stat')
    print(green('This will be committed as ' + message))
    if prompt('Go on?', default='y', validate='[yn]') == 'n':
        abort('Aborted')

    releases_git('commit -m "%s"' % message)
    releases_git('tag ' + tag)
    releases_git('push --tags origin master')
    local('git tag ' + tag)


def next_version(version):
    """Increase and return the version number.
    Makes sure the version is at least three numbers,
    e.g. 2.3.0

    """
    values = version.split('.')
    values += ('0',) * (3 - len(values))
    values[-1] = str(int(values[-1]) + 1)
    return '.'.join(values)


def set_version_number(version):
    with open('version.txt', 'w') as s:
        s.write(version)


@task
def clone_releases_repo():
    """Clones the releases repo into releases.git."""
    local('git clone --bare %s releases.git' % env.gitfab_releases_repo)
    #local('git --git-dir=releases.git config core.bare false')
    local('git --git-dir=releases.git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"')


@task
def deploy(version=None):
    """Deploy latest version, or a specific version if given as argument.

    """
    install_dir = env.gitfab_install_dir

    gitdir = install_dir + '/.git'
    if exists(gitdir):
        with cd(install_dir):
            run('git fetch')
            old_head = run('git rev-parse HEAD')
            old_version = run('git show HEAD:version.txt', pty=False)
            print 'Currently installed version:', repr(old_version)
    else:
        print(green(
            '%s does not exist, cloning it' %
            gitdir
        ))
        run('git clone %s %s' % (env.gitfab_releases_repo, install_dir))
        old_head = old_version = None

    with cd(install_dir):
        if version:
            new_version = version
        else:
            latest_version = run('git show origin/master:version.txt', pty=False)
            new_version = latest_version

        print green(
            'Switching from version %s (%s) to %s' %
            (old_version, old_head, new_version)
        )

        run('git reset --hard v' + new_version)

        if old_head:
            diff = run(
                'git diff --name-status %s v%s --' %
                (old_head, new_version),
                pty=False
            )
            updated_files = {}
            for line in diff.split('\n'):
                if line:
                    status, filename = line.split(None, 1)
                    updated_files[filename] = status
        else:
            # If there was no previous version, all files are "added"
            updated_files = dict(
                (f, 'A')
                for f in run('git ls-files', pty=False).split('\n')
                if f
            )

        if hasattr(env, 'gitfab_post_update'):
            env.gitfab_post_update(old_version, new_version, updated_files)


@task
def create_releases_repo():
    """Creates the releases repository on the repo server"""

    # This doesn't fail if the directory already exists,
    # but doesn't destroy anything.
    run('git --git-dir=%s init' % releases_repo_path)
    run(
        (
            'git --git-dir=%s --work-tree=. '
            'commit --allow-empty -m "Dummy initial commit"'
        ) % (
            releases_repo_path
        )
    )
