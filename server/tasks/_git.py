"""Implements a utility for cloning and querying Git repositories."""
import re
from enum import Enum
from tasks._check_output import check_output

_DIFF_NAME_STATUS_RE = re.compile(r'^(\w)\s+(.*)$')

Status = Enum('Status', 'ADDED DELETED UPDATED UNKNOWN')


def clone_from_github(path, dest, github_account=None):
    """A convenient version `clone` for GitHub hosted repositories.

    Args:
        path (str): the path to the GitHub repository. For example,
            "googleapis/discovery-artifact-manager".
        dest (str): the destination filepath.
        github_account (GitHubAccount, optional): the GitHub account to use to
            encode credentials into the hostname of the constructed repo URL.

    Raises:
        CallError: if the call returns a non-zero return code.

    Returns:
        Repository: the repository.
    """
    hostname = 'github.com'
    if github_account:
        hostname = '{}:{}@{}'.format(github_account.username,
                                     github_account.personal_access_token,
                                     hostname)
    url = 'https://{}/{}'.format(hostname, path)
    return clone(url, dest)


def clone(url, dest):
    """Clones the repository at `url` to `dest`.

    Args:
        url (str): the remote URL.
        dest (str): the destination filepath.

    Raises:
        CallError: if the call returns a non-zero return code.

    Returns:
        Repository: the repository.
    """
    check_call('git clone {} {}'.format(url, dest))
    return Repository(dest)


class Repository(object):
    """Represents a Git repository."""

    def __init__(self, filepath):
        self.filepath = filepath

    def add(self, paths):
        """Add file contents to the index.

        Args:
            paths (list(str)): a list of files to add content from.

        Raises:
            CallError: if the call returns a non-zero return code.
        """
        check_call('git add {}'.format(' '.join(paths)), cwd=self.filepath)

    def authors_since(self, rev):
        """Returns a list of emails of the authors of all commits since `rev`.

        Args:
            rev (str): a revision parameter. For example: "d1f3ffe7", or
                "0.13.2".

        Raises:
            CallError: if the call returns a non-zero return code.

        Returns:
            list(str): a list of emails of the authors of all commits since
                `rev`.
        """
        data = check_call('git log {}..HEAD --pretty=format:"%ae"'.format(rev),
                          cwd=self.filepath)
        return data.strip().split('\n')

    def commit(self, message, name, email):
        """Record changes to the repository.

        Args:
            message (str): the commit message.
            name (str): the user's name.
            email (str): the user's email.

        Raises:
            CallError: if the call returns a non-zero return code.
        """
        cmd = ('git -c user.name="{}" -c user.email="{}" commit -a'
               ' --allow-empty-message -m "{}"').format(name, email, message)
        check_call(cmd, cwd=self.filepath)

    def diff_name_status(self, rev=None, staged=True):
        """Return a list of status, filename pairs of changes from `rev`.

        Args:
            rev (str, optional): a revision parameter. If set, `staged` is
                ignored. For example: "d1f3ffe7", or "0.13.2".
            staged (bool, optional): if true, staged changes are returned.

        Raises:
            CallError: if the call returns a non-zero return code.

        Returns:
            list((Status, str)): a list of status, filename pairs of changes
                from HEAD.
        """
        cmd = 'git diff --name-status'
        if rev:
            cmd += ' {}..HEAD'.format(rev)
        elif staged:
            cmd = cmd + ' --staged'
        output = check_call(cmd, cwd=self.filepath).strip()
        pairs = []
        if not output:
            return pairs
        for line in output.split('\n'):
            # `split` doesn't *have* to return 2 strings, but it should behave
            # as expected on the command output.
            match = _DIFF_NAME_STATUS_RE.match(line)
            if not match:
                raise Exception('unexpected diff line format: {}'.format(line))
            status = {
                'A': Status.ADDED,
                'D': Status.DELETED,
                'M': Status.UPDATED
            }.get(match.group(1), Status.UNKNOWN)
            pairs.append((status, match.group(2)))
        return pairs

    def latest_tag(self):
        """Returns the latest tag.

        Raises:
            CallError: if the call returns a non-zero return code.

        Returns:
            str: the latest tag.
        """
        data = check_call('git describe --tags --abbrev=0', cwd=self.filepath)
        return data.strip()

    def push(self, remote='origin', branch='master', tags=False):
        """Updates remote refs.

        Args:
            remote (str): the remote name.
            branch (str): the branch name.
            tags (bool, optional): if true, only tags are pushed.

        Raises:
            CallError: if the call returns a non-zero return code.
        """
        cmd = 'git push {} {}'.format(remote, branch)
        if tags:
            cmd = 'git push {} --tags'.format(remote)
        check_call(cmd, cwd=self.filepath)

    def reset(self, rev, mode='soft'):
        """Resets current HEAD to `rev`.

        Args:
            rev (str): a revision parameter. For example: "d1f3ffe7",
                or "0.13.2".
            mode (str, optional): the type of reset to perform.

        Raises:
            CallError: if the call returns a non-zero return code.
        """
        cmd = 'git reset'
        if mode:
            cmd += ' --{}'.format(mode)
        check_call(cmd + ' HEAD~{}'.format(rev), cwd=self.filepath)

    def tag(self, name):
        """Creates a tag.

        Args:
            name (str): the name of the tag.

        Raises:
            CallError: if the call returns a non-zero return code.
        """
        check_call('git tag {}'.format(name), cwd=self.filepath)
