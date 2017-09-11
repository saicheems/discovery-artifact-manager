import glob
import json
import os
from os.path import join
from tempfile import TemporaryDirectory

from tasks import _git
from tasks._check_output import check_output

_REPO_NAME = 'discovery-artifact-manager'
_REPO_PATH = 'googleapis/discovery-artifact-manager'


def discovery_documents(filepath, preferred=False, skip=None):
    """Returns a map of API IDs to Discovery document filenames.

    Args:
        repo (tasks._git.Repository): the discovery-artifact-manager
            repository.
        preferred_only (bool, optional): if true, only APIs marked as
            preferred are returned.
        skip (list, optional): a list of API IDs to skip.

    Returns:
        dict(string, string): a map of API IDs to Discovery document
            filenames.
    """
    repo = _git.clone_from_github(_REPO_PATH, join(filepath, _REPO_NAME))
    filenames = glob.glob(join(repo.filepath, 'discoveries/*.json'))
    filenames = [x for x in filenames if os.path.basename(x) != 'index.json']
    ddocs = {}
    for filename in filenames:
        print(filename)
        id_ = None
        with open(filename) as file_:
            id_ = json.load(file_)['id']
            print(id_)
        if id_ in ddocs:
            continue
        ddocs[id_] = filename
    if skip:
        _ = [ddocs.pop(id_, None) for id_ in skip]
    if not preferred:
        return ddocs
    index = {}
    with open(join(repo.filepath, 'discoveries/index.json')) as file_:
        index = json.load(file_)
    for api in index['items']:
        id_ = api['id']
        if id_ in ['admin:directory_v1', 'admin:datatransfer_v1']:
            continue
        if api['preferred']:
            continue
        ddocs.pop(id_, None)
    return ddocs


def update(filepath, github_account):
    repo = _git.clone_from_github(
        _REPO_PATH, join(filepath, _REPO_NAME), github_account=github_account)
    with TemporaryDirectory() as gopath:
        os.makedirs(join(gopath, 'src'))
        check_output(['ln', '-s',
                      join(repo.filepath, 'src'),
                      join(gopath, 'src/discovery-artifact-manager')])
        env = os.environ.copy()
        env['GOPATH'] = gopath
        check_output(['go', 'run', 'src/main/updatedisco/main.go'],
                     cwd=repo.filepath,
                     env=env)
    repo.add(['discoveries'])
    commitmsg = 'Autogenerated Discovery document update'
    if not repo.diff_name_status():
        return
    repo.commit(commitmsg, github_account.name, github_account.email)
    repo.push()
