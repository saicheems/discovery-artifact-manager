"""Contains definitions/getters for GitHub and package manager accounts."""
from collections import namedtuple

from google.cloud import datastore

GitHubAccount = namedtuple('GitHubAccount',
                           'name email username personal_access_token')

NpmAccount = namedtuple('NpmAccount', 'auth_token')

RubyGemsAccount = namedtuple('RubyGemsAccount', 'api_key')

def get_github_account():
    """Returns the GitHub account stored in Datastore.

    Returns:
        GitHubAccount: a GitHub account.
    """
    client = datastore.Client()
    obj = list(client.query(kind='GitHubAccount').fetch())[0]
    return GitHubAccount(obj['name'], obj['email'], obj['username'],
                         obj['personal_access_token'])

def get_npm_account():
    """Returns the npm account stored in Datastore.

    Returns:
        NpmAccount: an npm account.
    """
    client = datastore.Client()
    obj = list(client.query(kind='NpmAccount').fetch())[0]
    return NpmAccount(obj['auth_token'])

def get_rubygems_account():
    """Returns the RubyGems account stored in Datastore.

    Returns:
        RubyGemsAccount: a RubyGems account.
    """
    client = datastore.Client()
    obj = list(client.query(kind='RubyGemsAccount').fetch())[0]
    return RubyGemsAccount(obj['api_key'])
