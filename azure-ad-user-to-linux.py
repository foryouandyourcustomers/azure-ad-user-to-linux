#!/usr/bin/env python3

"""
    sync user accounts from azure active directory to local linux machine
"""

import click
import sys
import requests
import logging

from az import AzureAd, AzureContainer
from users import User, sort_users_unique

@click.command()
@click.option(
    '--loglevel',
    required=False,
    envvar='LOGLEVEL',
    type=click.Choice(['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']),
    default="INFO",
    help="The loglevel for the script execution",
    show_default=True
)
@click.option(
    '--tenant-id',
    required=True,
    envvar='AZURE_TENANT_ID',
    help="The azure tenant id",
    show_default=True
)
@click.option(
    '--client-id',
    required=True,
    envvar='AZURE_CLIENT_ID',
    help="The azure service principal client id",
    show_default=True
)
@click.option(
    '--client-secret',
    required=True,
    envvar='AZURE_CLIENT_SECRET',
    help="The azure service principal client secret",
    show_default=True
)
@click.option(
    '--azure-ad-groups',
    required=True,
    envvar='AZURE_AD_GROUPS',
    help="A comma separated list of azure ad group ids to get users from",
    show_default=True
)
@click.option(
    '--azure-ad-username-field',
    required=True,
    envvar='AZURE_AD_USERNAME_FIELD',
    help="The field used to generate linux usernames from",
    default='userPrincipalName',
    show_default=True
)
@click.option(
    '--storage-account-name',
    required=True,
    envvar='STORAGE_ACCOUNT_NAME',
    help="The name of the storage account containing the users public ssh keys",
    show_default=True
)
@click.option(
    '--storage-account-container',
    required=True,
    envvar='STORAGE_ACCOUNT_CONTAINER',
    help="The name oof the blob container in the storage account which contains the users public ssh keys",
    show_default=True
)
@click.option(
    '--ssh-keys-prefix',
    envvar='SSH_KEYS_PREFIX',
    help="Filter files in the storage account container by prefix.",
    show_default=True
)
@click.option(
    '--ssh-keys-suffix',
    envvar='SSH_KEYS_SUFFIX',
    required=True,
    help="Filter files in the storage account container by prefix.",
    default=".pub",
    show_default=True
)

def run(loglevel, tenant_id, client_id, client_secret,
        azure_ad_groups, azure_ad_username_field,
        storage_account_name, storage_account_container,
        ssh_keys_prefix, ssh_keys_suffix):
    """
    synchronize azure ad users with local user accounts
    """

    logging.basicConfig(level=loglevel)
    # set warning loglevel for azure modules
    # we dont want to spam the log if set to debug or info!
    logging.getLogger('azure.core').setLevel(logging.ERROR)
    logging.getLogger('azure.identity').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.getLogger('msal').setLevel(logging.ERROR)

    # initialize azure ad client
    try:
        azad = AzureAd(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
    except Exception as e:
        logging.error(f'Unable to connect to Azure AD')
        raise e

    # intialize storage account client
    try:
        azcontainer = AzureContainer(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            storage_account_name=storage_account_name,
            storage_account_container=storage_account_container
        )
    except Exception as e:
        logging.error(f'Unable to connect to Azure Storage Account')
        raise e

    # retrieve azure ad users from the specified groups
    members = []
    for g in azure_ad_groups.split(','):
        try:
            for m in azad.get_group_members(group_id=g):
                members.append(
                    User(**m, ssh_keys_prefix=ssh_keys_prefix, ssh_keys_suffix=ssh_keys_suffix)
                )
        except Exception as e:
            logging.warning(e)
    members = sort_users_unique(members)

    # retrieve ssh keys for each of the retrieved azure ad users
    # from keyvault
    blobs = []
    try:
        blobs = azcontainer.get_blobs(prefix=ssh_keys_prefix, suffix=ssh_keys_suffix)
    except Exception as e:
        logging.warning(e)

    # checking returned blobs against username list
    # and download any blob that matches a user account
    # an ssh key is always set up in this format
    # <prefix><user principal name><.optional identifier><suffix>
    for m in members:
        if m.account_enabled:
            keys = [k for k in blobs if m.valid_ssh_keys.search(k.get('name', ''))]
            if not keys:
                logging.warning(f'No public ssh keys found for {m.user_principal_name}')
            else:
                # download the keys and store them in the user object
                for k in keys:
                    try:
                        m.ssh_keys.append(azcontainer.download_blob(k.get('name')))
                    except Exception as e:
                        logging.warning(f'Unable to download ssh pub key {k}: {e}')


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
    except Exception as error:
        logging.error(error)
        sys.exit(1)


