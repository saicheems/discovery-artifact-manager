from unittest.mock import Mock, patch

from tasks import _accounts


@patch('google.cloud.datastore.Client', autospec=True)
def test_get_github_account(ClientMock):
    query_mock = Mock()
    query_mock.return_value.fetch.return_value = [{
        'name': 'Test',
        'email': 'test@example.com',
        'username': 'test',
        'personal_access_token': 'token'
    }]
    ClientMock.return_value.query = query_mock
    expected = _accounts.GitHubAccount(
        'Test', 'test@example.com', 'test', 'token')
    actual = _accounts.get_github_account()
    query_mock.assert_called_once_with(kind='GitHubAccount')
    assert actual == expected


@patch('google.cloud.datastore.Client', autospec=True)
def test_get_npm_account(ClientMock):
    query_mock = Mock()
    query_mock.return_value.fetch.return_value = [{
        'auth_token': 'token'
    }]
    ClientMock.return_value.query = query_mock
    expected = _accounts.NpmAccount('token')
    actual = _accounts.get_npm_account()
    query_mock.assert_called_once_with(kind='NpmAccount')
    assert actual == expected


@patch('google.cloud.datastore.Client', autospec=True)
def test_get_rubygems_account(ClientMock):
    query_mock = Mock()
    query_mock.return_value.fetch.return_value = [{
        'api_key': 'key'
    }]
    ClientMock.return_value.query = query_mock
    expected = _accounts.RubyGemsAccount('key')
    actual = _accounts.get_rubygems_account()
    query_mock.assert_called_once_with(kind='RubyGemsAccount')
    assert actual == expected
