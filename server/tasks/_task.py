"""Implements the base class for a task."""
from tempfile import TemporaryDirectory
from tasks import _accounts


class Task(object):  # pylint: disable=too-few-public-methods
    """Base class for a task."""
    def __init__(self):
        self.github_account = _accounts.get_github_account()

    def run(self):
        """Runs the task."""
        with TemporaryDirectory() as filepath:
            self._run(filepath)

    def _run(self, filepath):
        pass
