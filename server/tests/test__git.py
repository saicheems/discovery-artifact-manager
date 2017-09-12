from unittest.mock import patch

import pytest

from tasks import _accounts, _git


@patch('tasks._git.check_output', autospec=True)
def test_clone_from_github(check_output_mock):
    repo = _git.clone_from_github('example/myrepo', '/tmp')
    check_output_mock.assert_called_once_with(
        ['git', 'clone', 'https://github.com/example/myrepo', '/tmp'])
    assert repo.filepath == _git.Repository('/tmp').filepath

    check_output_mock.reset_mock()
    github_account = _accounts.GitHubAccount(
        'Test', 'test@example.com', 'test', 'token')
    repo = _git.clone_from_github(
        'example/myrepo', '/tmp', github_account=github_account)
    check_output_mock.assert_called_once_with(
        ['git', 'clone',
         'https://test:token@github.com/example/myrepo', '/tmp'])
    assert repo.filepath == _git.Repository('/tmp').filepath


@pytest.fixture()
def repo():
    return _git.Repository('/tmp')


@patch('tasks._git.check_output', autospec=True)
def test_repository_add(check_output_mock, repo):
    repo.add(['src'])
    check_output_mock.assert_called_once_with(
        ['git', 'add', 'src'], cwd='/tmp')


@patch('tasks._git.check_output', autospec=True)
def test_repository_add_multiple_filepaths(check_output_mock, repo):
    repo.add(['hello', 'world'])
    check_output_mock.assert_called_once_with(
        ['git', 'add', 'hello', 'world'], cwd='/tmp')


@patch('tasks._git.check_output', autospec=True)
def test_repository_authors_since_one(check_output_mock, repo):
    check_output_mock.return_value = 'example@example.com'
    authors = repo.authors_since('HEAD~1')
    check_output_mock.assert_called_once_with(
        ['git', 'log', 'HEAD~1..HEAD', '--pretty=format:"%ae"'], cwd='/tmp')
    assert authors == ['example@example.com']


@patch('tasks._git.check_output', autospec=True)
def test_repository_authors_since_multiple(check_output_mock, repo):
    check_output_mock.return_value = 'example@example.com\ntest@test.com'
    authors = repo.authors_since('HEAD~2')
    check_output_mock.assert_called_once_with(
        ['git', 'log', 'HEAD~2..HEAD', '--pretty=format:"%ae"'], cwd='/tmp')
    assert authors == ['example@example.com', 'test@test.com']


@patch('tasks._git.check_output', autospec=True)
def test_repository_checkout(check_output_mock, repo):
    repo.checkout('docs')
    check_output_mock.assert_called_once_with(
        ['git', 'checkout', 'docs'], cwd='/tmp')


@patch('tasks._git.check_output', autospec=True)
def test_repository_commit(check_output_mock, repo):
    repo.commit('hello world', 'example name', 'example@example.com')
    check_output_mock.assert_called_once_with(
        ['git',
         '-c', 'user.name=example name',
         '-c', 'user.email=example@example.com',
         'commit', '-a', '--allow-empty-message', '-m', 'hello world'],
        cwd='/tmp')


@patch('tasks._git.check_output', autospec=True)
def test_repository_diff_name_status_none(check_output_mock, repo):
    check_output_mock.return_value = ''
    pairs = repo.diff_name_status()
    check_output_mock.assert_called_once_with(
        ['git', 'diff', '--name-status', '--staged'], cwd='/tmp')
    assert pairs == []


@patch('tasks._git.check_output', autospec=True)
def test_repository_diff_name_status_none_staged(check_output_mock,
                                                 repo):
    check_output_mock.return_value = ''
    pairs = repo.diff_name_status(staged=False)
    check_output_mock.assert_called_once_with(
        ['git', 'diff', '--name-status'], cwd='/tmp')
    assert pairs == []


@patch('tasks._git.check_output', autospec=True)
def test_repository_diff_name_status_none_rev(check_output_mock, repo):
    check_output_mock.return_value = ''
    pairs = repo.diff_name_status(rev='HEAD~1')
    check_output_mock.assert_called_once_with(
        ['git', 'diff', '--name-status', 'HEAD~1..HEAD'], cwd='/tmp')
    assert pairs == []


@patch('tasks._git.check_output', autospec=True)
def test_repository_diff_name_status_one(check_output_mock, repo):
    check_output_mock.return_value = 'A\t/tmp/hello.txt'
    pairs = repo.diff_name_status()
    assert pairs == [('/tmp/hello.txt', _git.Status.ADDED)]


@patch('tasks._git.check_output', autospec=True)
def test_repository_diff_name_status_multiple(check_output_mock, repo):
    check_output_mock.return_value = ('A\t/tmp/hello.txt\n'
                                      'D\t/tmp/world.txt\n'
                                      'M\t/tmp/foo.txt\n'
                                      'X\t/tmp/bar.txt')
    pairs = repo.diff_name_status()
    assert pairs == [('/tmp/hello.txt', _git.Status.ADDED),
                     ('/tmp/world.txt', _git.Status.DELETED),
                     ('/tmp/foo.txt', _git.Status.UPDATED),
                     ('/tmp/bar.txt', _git.Status.UNKNOWN)]


@patch('tasks._git.check_output', autospec=True)
def test_repository_latest_tag(check_output_mock, repo):
    check_output_mock.return_value = 'v0.1'
    tag = repo.latest_tag()
    check_output_mock.assert_called_once_with(
        ['git', 'describe', '--tags', '--abbrev=0'], cwd='/tmp')
    assert tag == 'v0.1'


@patch('tasks._git.check_output', autospec=True)
def test_repository_push(check_output_mock, repo):
    repo.push()
    check_output_mock.assert_called_once_with(
        ['git', 'push', 'origin', 'master'], cwd='/tmp')


@patch('tasks._git.check_output', autospec=True)
def test_repository_push_remote_branch(check_output_mock, repo):
    repo.push(remote='github', branch='dev')
    check_output_mock.assert_called_once_with(
        ['git', 'push', 'github', 'dev'], cwd='/tmp')


@patch('tasks._git.check_output', autospec=True)
def test_repository_push_tags(check_output_mock, repo):
    repo.push(tags=True)
    check_output_mock.assert_called_once_with(
        ['git', 'push', 'origin', '--tags'], cwd='/tmp')


@patch('tasks._git.check_output', autospec=True)
def test_repository_soft_reset(check_output_mock, repo):
    repo.soft_reset('HEAD~1')
    check_output_mock.assert_called_once_with(
        ['git', 'reset', '--soft', 'HEAD~1'], cwd='/tmp')


@patch('tasks._git.check_output', autospec=True)
def test_repository_tag(check_output_mock, repo):
    repo.tag('v0.1')
    check_output_mock.assert_called_once_with(
        ['git', 'tag', 'v0.1'], cwd='/tmp')
