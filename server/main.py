import glob
import json
import os
import re
import shlex
import subprocess
from collections import namedtuple
from datetime import date
from tempfile import TemporaryDirectory

from flask import Flask, abort, request
from google.cloud import datastore

app = Flask(__name__)

_DEVNULL = open(os.devnull, 'w')

GitHubAccount = namedtuple('GitHubAccount',
                           'name email username personal_access_token')


def _get_github_account():
    """Returns the GitHub account stored in Datastore.

    Returns:
        GitHubAccount: a GitHub account.
    """
    ds = datastore.Client()
    account = list(ds.query(kind='GitHubAccount').fetch())[0]
    return GitHubAccount(account['name'], account['email'],
                         account['username'], account['personal_access_token'])


def _call(cmd, check=False, **kwargs):
    """A wrapper over subprocess.call that splits cmd with shlex.split

    If check is True, then check_call is run instead of call.

    Args:
        cmd (string): A command to run.
        check (bool, optional): If true, check_call is run instead of call.

    Returns:
        int: The return code of the call.
    """
    func = subprocess.call
    if check:
        func = subprocess.check_call
    return func(shlex.split(cmd), **kwargs)


@app.route('/cron/discoveries')
def cron_discoveries():
    # This header can't be spoofed, see
    # https://cloud.google.com/appengine/docs/flexible/python/scheduling-jobs-with-cron-yaml#securing_urls_for_cron
    if request.headers.get('X-Appengine-Cron') is None:
        abort(403)

    with TemporaryDirectory() as tmp_dir:
        go_dir = os.path.join(tmp_dir, 'go')      # /tmp/go
        os.makedirs(os.path.join(go_dir, 'src'))  # mkdir -p /tmp/go/src

        # /tmp/discovery-artifact-manager
        dartman_dir = os.path.join(tmp_dir, 'discovery-artifact-manager')
        _call(('git clone'
               ' https://github.com/googleapis/discovery-artifact-manager'
               ' {}').format(dartman_dir), check=True)

        # ln -s /tmp/discovery-artifact-manager/src \
        #       /tmp/go/src/discovery-artifact-manager
        _call('ln -s {} {}'.format(
            os.path.join(dartman_dir, 'src'),
            os.path.join(go_dir, 'src', 'discovery-artifact-manager')),
              check=True)

        env = os.environ.copy()
        env['GOPATH'] = go_dir

        _call('go run src/main/updatedisco/main.go', check=True,
              cwd=dartman_dir, env=env)

        _call('git add discoveries', check=True, cwd=dartman_dir)

        account = _get_github_account()

        returncode = _call(
            ('git -c user.name="{}" -c user.email="{}"'
             ' commit -m "Autogenerated Discovery document update"').format(
                 account.name, account.email),
            cwd=dartman_dir)

        # `returncode` is non-zero if there's nothing to commit.
        if not returncode:
            remote_url = ('https://{}:{}@github.com'
                          '/googleapis/discovery-artifact-manager')
            remote_url = remote_url.format(account.username,
                                           account.personal_access_token)

            # Send output to /dev/null so `remote_url` isn't logged.
            _call('git remote add github {}'.format(remote_url), check=True,
                  cwd=dartman_dir, stdout=_DEVNULL, stderr=_DEVNULL)
            _call('git push github', check=True, cwd=dartman_dir,
                  stdout=_DEVNULL, stderr=_DEVNULL)

    return ''


@app.route('/cron/clients/php')
def cron_clients_php():
    if request.headers.get('X-Appengine-Cron') is None:
        abort(403)

    with TemporaryDirectory as tmp_dir:
        # /tmp/discovery-artifact-manager
        dartman_dir = os.path.join(tmp_dir, 'discovery-artifact-manager')
        _call(('git clone'
               ' https://github.com/googleapis/discovery-artifact-manager'
               ' {}').format(dartman_dir), check=True)

        # /tmp/google-api-php-client-services
        client_lib_dir = os.path.join(tmp_dir, 'google-api-php-client-services')
        _call(('git clone'
               ' https://github.com/saicheems/google-api-php-client-services'
               ' {}').format(client_lib_dir), check=True)

        index_filename = os.path.join(dartman_dir, 'discoveries', 'index.json')
        preferred = {}
        with open(index_filename) as file_:
            root = json.load(file_)
            for api in root['items']:
                preferred[api['id']] = api['preferred']
        # "admin:directory_v1" and "admin:directorytransfer_v1" are incorrectly
        # marked as not preferred.
        preferred['admin:directory_v1'] = True
        preferred['admin:datatransfer_v1'] = True

        # Glob a list of all Discovery documents in discovery-artifact-manager.
        discovery_document_filenames = glob.glob(
            os.path.join(dartman_dir, 'discoveries', '*.json'))
        # Skip index.json.
        discovery_document_filenames = [
            filename for filename in discovery_document_filenames
            if os.path.basename(filename) != 'index.json']

        # /tmp/venv
        venv_dir = os.path.join(tmp_dir, 'venv')
        # Create a Python 2.7 virtualenv.
        _call('virtualenv {}'.format(venv_dir), check=True)
        # Install the Google API client generator.
        _call('{} setup.py install'.format(
            os.path.join(venv_dir, 'bin', 'python')), check=True,
              cwd=os.path.join(dartman_dir, 'google-api-client-generator'))

        # /tmp/google-api-php-client-services/src/Google/Service
        service_dir = os.path.join(client_lib_dir, 'src', 'Google', 'Service')

        account = _get_github_account()

        returncode = -1
        for filename in discovery_document_filenames:
            root = {}
            with open(filename) as file_:
                root = json.load(file_)
            id_ = root['id']
            name = root['name']
            version = root['version']

            # Skip the "discovery" and any non-preferred services.
            if name == 'discovery':
                continue
            if not preferred[id_]:
                continue

            # Generate the service into another temporary directory, so it's
            # possible to decide if any service files should be deleted.
            with TemporaryDirectory() as tmp_dir2:
                # Generate the service into /tmp2/.
                _call(('bin/generate_library'
                       ' --input {}'
                       ' --language php'
                       ' --language_variant 1.2.0'
                       ' --output_dir {}').format(filename, tmp_dir2),
                      check=True, cwd=venv_dir)

                dirs = os.listdir(tmp_dir2)
                # Drop the extension if it's there.
                # ex: "BigQuery" instead of "BigQuery.php".
                service_name = os.path.splitext(dirs[0])[0]
                # Delete the original service and service directory.
                # rm -rf /tmp/google-api-php-client-services/src/Google/Service/Foo.php \
                #        /tmp/google-api-php-client-services/src/Google/Service/Foo
                _call('rm -rf {}.php {}'.format(
                    os.path.join(service_dir, service_name),
                    os.path.join(service_dir, service_name)),
                      check=True)
                # Copy the newly generated service back.
                # cp /tmp2/Foo.php /tmp/google-api-php-client-services/src/Google/Service/Foo.php
                _call('cp {}.php {}'.format(
                    os.path.join(tmp_dir2, service_name), service_dir),
                      check=True)
                # cp -r /tmp2/Foo /tmp/google-api-php-client-services/src/Google/Service/Foo
                _call('cp -r {} {}'.format(
                    os.path.join(tmp_dir2, service_name), service_dir),
                      check=True)

            # Stage all changes.
            _call('git add src', check=True, cwd=client_lib_dir)

            commitmsg = 'Autogenerated update for {} version {} ({})'.format(
                name, version, date.today().isoformat())
            cmd = 'git -c user.name="{}" -c user.email="{}" commit -a -m "{}"'
            cmd = cmd.format(account.name, account.email, commitmsg)
            # A zero return code means there's something to push.
            if _call(cmd, cwd=client_lib_dir) == 0:
                returncode = 0

        # `returncode` is non-zero if there's nothing to commit.
        if not returncode:
            # Grab the latest tag.
            output = subprocess.check_output(
                shlex.split('git describe --tags --abbrev=0'),
                cwd=client_lib_dir)
            latest_tag = output.decode('utf-8').strip()

            # `version_re` matches versions like "v0.12".
            version_re = re.compile(r'^(v[0-9]+)\.([0-9]+)$')
            match = version_re.match(latest_tag)
            if not match:
                raise Exception(
                    'latest tag does not match the pattern \'{}\': {}'.format(
                        version_re.pattern, latest_tag))

            # ex: '12'
            minor_revision = match.group(2)
            # ex: '13'
            new_minor_revision = str(int(minor_revision) + 1)
            # ex: 'v1.13'
            new_version = version_re.sub(
                r'\1.{}'.format(new_minor_revision), latest_tag)

            _call('git tag {}'.format(new_version), check=True,
                  cwd=client_lib_dir)

            remote_url = ('https://{}:{}@github.com'
                          '/saicheems/google-api-php-client-services')
            remote_url = remote_url.format(account.username,
                                           account.personal_access_token)

            # Send output to /dev/null so `remote_url` isn't logged.
            _call('git remote add github {}'.format(remote_url), check=True,
                  cwd=dartman_dir, stdout=_DEVNULL, stderr=_DEVNULL)
            _call('git push github', check=True, cwd=dartman_dir,
                  stdout=_DEVNULL, stderr=_DEVNULL)
            # Tags have to be pushed separately.
            cmd = 'git push github --tags'
            _call(shlex.split(cmd), check=True, cwd=client_lib_dir,
                  stdout=_DEVNULL, stderr=_DEVNULL)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
