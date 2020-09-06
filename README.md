auto-backup
===========

Python program for automating backup tasks.

Features
--------

* Synchronize remote data into a local copy using
  [Rclone](https://rclone.org/). This can be used to get copies of contacts
  and calendars using CardDAV and CalDAV protocols.
* Backup local data using [BorgBackup](https://www.borgbackup.org/).
* Remove / prune old backups
* Send notifications in case of an error or with a summary of the
  backups of the last 24 hours.
* Use [XMPP](https://pypi.org/project/aioxmpp/) for notifications using
* A single [TOML](https://pypi.org/project/toml/) file for configuring
  all tasks

Setup
-----

The poetry, rclone and borg command line tools must be installed on the
target machine. Clone this repository and install it

    poetry install

This will create a virtual environment to isolate the installation and
will download and install all dependencies listed in the poetry.lock file.

Usage
-----

Call the module an pass the path to a configuration file as
sole argument

    python -m auto-backup <config-file>

You can execute a subset of all tasks by using the `--tag` option. This
option can be given multiple times

    python -m auto-backup --tag tag1 --tag tag2 <config-file>

This will execute all tasks which have at least one of the two tags
assigned to it.

Configuration File
------------------

### XMPP notifications

The configuration must contain valid XMPP credentials and a
recipient a recipient for the notifications. Add those in
the XMPP section

    [XMPP]
    account   = "user@server"
    password  = "password"
    recipient = "other_user@some_server"

### Tasks

The configuration file must contain a list of tasks. Each task is
a dictionary with at least type and name keys

    [[tasks]]
    type = "rclone"
    name = "Sync some data before backup"

    [[tasks]]
    type = "backup"
    name = "Create a backup"

Tasks are executed in the order given in the configuration file.

You may also provide a list of tags for each task to allow executing
a subset of all tasks

    [[tasks]]
    type = "backup"
    name = "Create a backup"
    tags = ["mytag"]

Use the `--tag mytag` command line option to specify which tasks shall
be run.

Tasks may required additional key value pairs. See the task specific
sections for information about which keys are necessary. If you have
multiple tasks of the same type you can share key value pairs between
them. Put the shared data into a section named with the task type. You
can override shared values in individual tasks

    [rclone]
    configFile = "/my/rclone.conf"

    [[tasks]]
    # This one will use the configFile given in the [rclone] section
    type = "rclone"
    name = "Sync contact data"

    [[tasks]]
    # Override configFile
    type = "rclone"
    name = "Sync calendar data"
    configFile = "/other/config/file.conf"

### Rclone tasks

You have to install Rclone by your own and create a configuration file
containing the required remotes. Add the path to the file in the TOML
configuration. Use `rclone` for the type and provide the following
key value pairs

    [[tasks]]
    type        = "rclone"
    name        = "Sync data"
    configFile  = "/some/path/rclone.conf"
    source      = "remote:path"
    destination = "/local/directory"

Use the Rclone notation for the source value.

### Backup tasks

Requires the `borg` command to be present. Use `backup`
as task type and provide the following key value pairs

    [[tasks]]
    type       = "backup"
    name       = "Backup some data"
    source     = "/local/directory"
    repository = "repo1"

The `repository` is the name of a BorgBackup repository. You
must add repositories in their own section

    [repositories]
    repo1.url      = "ssh://user@server:port/remote/path/to/repo"
    repo1.password = "repo encryption key"

You may also provide exclude patterns

    [[tasks]]
    type       = "backup"
    name       = "Backup some data"
    source     = "/local/directory"
    repository = "repo1"
    excludes   = [".gitignore", "sh:**/.gitignore"]

See [borg create](https://borgbackup.readthedocs.io/en/stable/usage/create.html)
for information about the underlying borg call and pattern syntax.

### Prune tasks

Requires the `borg` command to be present. Use `prune`
as task type and provide the following key value pairs

    [[tasks]]
    type       = "prune"
    name       = "Prune old backups"
    repository = "repo1"
    within     = "7d"
    daily      = 10
    weekly     = 7
    monthly    = 12

See [borg prune](https://borgbackup.readthedocs.io/en/stable/usage/prune.html)
for the meaning of the within, daily, weekly and monthly values. See the
[backup task](#Backup-tasks) for information about respositories.

### Check tasks

This task checks the number of backups in the last 24 hours for a
set of repositories. It will send a notification containing the
results to the [recipient configured](#XMPP-notifications).

Requires the `borg` command to be present. Use `check`
as task type and provide the following key value pairs

    [[tasks]]
    type       = "check"
    name       = "Check todays backups"
    repository = ["repo1", "repo2"]

See the [backup task](#Backup-tasks) for information about
respositories.

Todo's
------

* [x] Use poetry for environment management
* [ ] Add [black](https://pypi.org/project/black/) and 
      [isort](https://pypi.org/project/isort/) lint support
* [ ] Add [pytest](https://docs.pytest.org) unit tests and
      [pytest-cov](https://pypi.org/project/pytest-cov/) for coverage
* [ ] Check for code style with 
      [pytest-isort](https://pypi.org/project/pytest-isort/) and
      [pytest-black](https://pypi.org/project/pytest-black/)
* [ ] Use static types with [mypy](http://www.mypy-lang.org/)
* [ ] Use [MutMut](https://pypi.org/project/mutmut/) for mutation testing
* [ ] Git hooks with [pre-commit](https://pre-commit.com/)
* [ ] GitHub Actions or Azure pipelie for continous integration
* [ ] Provide complete distribution package on GitHub
