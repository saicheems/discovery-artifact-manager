import glob
import os
from tasks import _git

def clone(filepath, github_account=None):
    return _git.clone_from_github(
        'googleapis/discovery-artifact-manager', filepath, github_account)


def discovery_documents(repo, preferred_only=True, skip_discovery_v1=True):
    """Returns a map of API IDs to Discovery document filenames.

    Args:
        repo (tasks._git.Repository): the discovery-artifact-manager
            repository.
        preferred_only (bool, optional): if true, only APIs marked as
            preferred are returned.
        skip_discovery_v1 (bool, optional): if true, `discovery:v1` is not
            included in the APIs returned.

    Returns:
        dict(string, string): a map of API IDs to Discovery document
            filenames.
    """
    filenames = glob.glob(os.path.join(repo.filepath, 'discoveries', '*.json'))
    filenames = [x for x in filenames if os.path.basename(x) != 'index.json']
    discovery_documents = {}
    for filename in filenames:
        data = {}
        with open(filename) as file_:
            data = json.load(file_)
        id_ = data['id']
        if id_ in discovery_documents:
            continue
        preferred = data.get('preferred', False)
        if id_ in ['admin:directory_v1', 'admin:datatransfer_v1']:
            preferred = True
        if skip_discovery_v1 and id_ == 'discovery:v1':
            continue
        if preferred_only and not preferred:
            continue
        discovery_documents[id_] = filename
    return discovery_documents
