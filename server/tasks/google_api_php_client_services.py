"""Contains update/release functions for google-api-php-client-services."""
import re
from tempfile import TemporaryDirectory

import os
from os.path import join

from tasks import _check_output, _commit_message, _git
from tasks._check_output import check_output

# Matches strings like ".../src/Google/Service/BigQuery.php".
_SERVICE_FILENAME_RE = re.compile(r'src/Google/Service/[^/]+\.php$')
# Matches strings like "v0.12".
_VERSION_RE = re.compile(r'^v0\.([0-9]+)$')


def _generate_client(repo, venv_filepath, ddoc_filename):
    client_filepath = join(repo.filepath, 'src/Google/Service')
    with TemporaryDirectory() as dest_filepath:
        check_output([join(venv_filepath, 'bin/generate_library'),
                      '--input={}'.format(ddoc_filename),
                      '--language=php',
                      '--language_variant=1.2.0',
                      '--output_dir={}'.format(dest_filepath)])
        dirs = os.listdir(dest_filepath)
        client_name = os.path.splitext(dirs[0])[0]  # ex: "BigQuery"
        old_client_filepath = join(client_filepath, client_name)
        old_client_filename = '{}.php'.format(old_client_filepath)
        check_output(['rm', '-rf', old_client_filename, old_client_filepath])
        new_client_filepath = join(dest_filepath, client_name)
        new_client_filename = '{}.php'.format(new_client_filepath)
        check_output(['cp', new_client_filename, old_client_filename])
        check_output(['cp', '-r', new_client_filepath, old_client_filepath])


def _generate_and_commit_all_clients(repo, venv_filepath, discovery_documents):
    statuses = {}
    for id_, ddoc_filename in discovery_documents.items():
        _generate_client(repo, venv_filepath, ddoc_filename)
        repo.add(['src'])
        diff_ns = repo.diff_name_status()
        # By default, assume no files changed.
        statuses[id_] = None
        if not diff_ns:
            continue
        # If any files changed, the client was updated.
        statuses[id_] = _git.Status.UPDATED
        # If the service file is new, the client was added.
        for filename, status in diff_ns:
            match = _SERVICE_FILENAME_RE.match(filename)
            if match and status == _git.Status.ADDED:
                statuses[id_] = _git.Status.ADDED
                break
        repo.commit('', '_', '_')
    added = {k for k, v in statuses.items() if v == _git.Status.ADDED}
    updated = {k for k, v in statuses.items() if v == _git.Status.UPDATED}
    return added, updated


def _run_tests(repo):
    check_output(['composer', 'update'], cwd=repo.filepath)
    check_output(['vendor/bin/phpunit', '-c', '.'], cwd=repo.filepath)


def clone(filepath, github_account):
    return _git.clone_from_github('google/google-api-php-client-services',
                                  filepath,
                                  github_account=github_account)


def update(repo, discovery_documents, github_account):
    venv_filepath = join(repo.filepath, 'venv')
    check_output(['virtualenv', venv_filepath])
    check_output([join(venv_filepath, 'bin/pip'),
                  'install',
                  'google-apis-client-generator==1.4.3'])
    added, updated = _generate_and_commit_all_clients(
        repo, venv_filepath, discovery_documents)
    commit_count = len(added) + len(updated)
    if commit_count == 0:
        return
    _run_tests(repo)
    repo.reset('HEAD~{}'.format(commit_count))
    commitmsg = _commit_message.build(added, None, updated)
    repo.commit(commitmsg, github_account.name, github_account.email)
    repo.push()


def release(repo, github_account):
    latest_tag = repo.latest_tag()
    authors = repo.authors_since(latest_tag)
    if not authors or not all([x == github_account.email for x in authors]):
        return
    match = _VERSION_RE.match(latest_tag)
    if not match:
        raise Exception(
            'latest tag does not match the pattern \'{}\': {}'.format(
                _VERSION_RE.pattern, latest_tag))
    _run_tests(repo)
    minor_version = match.group(1)
    new_minor_version = str(int(minor_version) + 1)
    new_version = 'v0.{}'.format(new_minor_version)
    repo.tag(new_version)
    repo.push(tags=True)