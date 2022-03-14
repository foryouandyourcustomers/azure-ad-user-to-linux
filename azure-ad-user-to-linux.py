#!/usr/bin/env python3

"""
    sync user accounts from azure active directory to local linux machine
"""

import click
import sys
import requests
import logging
from azure.identity import ClientSecretCredential

def return_azure_ad_graph_token(tenant_id, client_id, client_secret):
    """
    login to azure and create azure ad graph token

    :param tenant_id:
    :param client_id:
    :param client_secret:
    :return: str
    """

    credentials = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )

    token = credentials.get_token('https://graph.microsoft.com/.default')

    return token.token

def return_azure_ad_group_members(group_id, token):
    """
    return a list of group members of the given group id
    :param group_id:
    :param token:
    :return: list
    """

    # authorize request with the given token
    headers = { 'Authorization': f'Bearer {token}'}
    # select only certain fields from the user list
    params = {
        '$select': 'displayName,mail,userPrincipalName,accountEnabled'
    }
    #$select=displayName,givenName,postalCode,identities
    r = requests.get(
        url=f'https://graph.microsoft.com/v1.0/groups/{group_id}/members',
        headers=headers,
        params=params
    )
    r.raise_for_status()

    members = r.json().get('value', [])
    if not members:
        raise ValueError(f'No members in group {group_id} found.')

    return members

@click.command()
@click.option(
    '--tenant-id',
    required=True,
    envvar='AZURE_TENANT_ID',
    help="The azure tenant id"
)
@click.option(
    '--client-id',
    required=True,
    envvar='AZURE_CLIENT_ID',
    help="The azure service principal client id"
)
@click.option(
    '--client-secret',
    required=True,
    envvar='AZURE_CLIENT_SECRET',
    help="The azure service principal client secret"
)
@click.option(
    '--azure-ad-groups',
    required=True,
    envvar='AZURE_AD_GROUPS',
    help="A comma separated list of azure ad group ids to get users from"
)
def run(tenant_id, client_id, client_secret, azure_ad_groups):
    """
    run azure ad sync to local fs

    :param tenant_id:
    :param client_id:
    :param client_secret:
    :return:
    """

    # login to azure with the given service principal and return azure graph bearer token
    token = return_azure_ad_graph_token(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )

    # retrieve users from the specified groups
    members = []
    for g in azure_ad_groups.split(','):
        try:
            m = return_azure_ad_group_members(group_id=g, token=token)
        except Exception as e:
            logging.warning(e)

        members.extend(m)

    # retrieve ssh keys for each of the retrieved azure ad users
    # from keyvault

    # ensure local managed group exists

    # get local users in managed group

    # verify local users against retrieved ad user objects
    # is the user enabled?
    # does the user exist in azure ad and locally?

    # create missing local users
    # add local users to managed group and to additional groups (for sudo etc)

    # disable local users by setting nologin shell

    # iterate over local users and manage ssh keys in authorized keys file
    # are the public keys in the authorized_keys? if not add them
    # are there any other authorized keys in the file which arent in the storage accoutn?
    # remove them

if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        logging.error(e)
        sys.exit(1)


