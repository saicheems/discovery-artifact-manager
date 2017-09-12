from tasks import _accounts

GITHUB_ACCOUNT = _accounts.GitHubAccount('Test', 'test@test.com', '_', '_')


def clone_from_github_mock_side_effect(repo_mock):
    def side_effect(path, dest, github_account=None):
        repo_mock.filepath = dest
        return repo_mock
    return side_effect
