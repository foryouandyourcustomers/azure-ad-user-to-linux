#!/usr/bin/env python3

"""
    sync user accounts from azure active directory to local linux machine
"""

import click
import sys
import requests
import logging

from az import AzureAd, AzureContainer
from users import AdUser, sort_ad_users_unique, LinuxGroup, LinuxUser


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
@click.option(
    '--linux-group-name',
    envvar='LINUX_GROUP_NAME',
    required=True,
    help="Group identifing users managed by the azure-ad-user-to-linux script.",
    default="azure-ad-users-to-linux",
    show_default=True
)

def run(loglevel, tenant_id, client_id, client_secret,
        azure_ad_groups, azure_ad_username_field,
        storage_account_name, storage_account_container,
        ssh_keys_prefix, ssh_keys_suffix,
        linux_group_name):
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

    # ensure local managed group exists to identify user accounts managed by azure-ad-users-to-linux
    try:
        lxgroup = LinuxGroup(name=linux_group_name)
        lxgroup.create()
    except Exception as e:
        logging.error(f'Unable to create linux group {linux_group_name}')
        raise e

    # retrieve azure ad users from the specified groups
    azure_ad_users = []
    for g in azure_ad_groups.split(','):
        group_members = []
        try:
            group_members = azad.get_group_members(group_id=g, additional_fields=[azure_ad_username_field])
            for m in group_members:
                # setup ad user object
                aduser = AdUser(**m)
                # add aduser to the retrieved members
                azure_ad_users.append(aduser)
        except Exception as e:
            logging.error(f'Unable to retrieve members of azure ad group {g}')
            raise e
    # sort all members and drop duplicates
    azure_ad_users = sort_ad_users_unique(azure_ad_users)

    # retrieve ssh keys for each of the retrieved azure ad users
    # from keyvault
    blobs = []
    try:
        blobs = azcontainer.get_blobs(prefix=ssh_keys_prefix, suffix=ssh_keys_suffix)
    except Exception as e:
        logging.warning(e)

    # with all information retrieved from azure ad and storage accounts
    # lets setup the linux user objects. the linux user objects
    # contain the public key files username etc
    linux_users = []
    for u in azure_ad_users:
        # set linux user object with a hopefully valid linux username ;-)
        try:
            lu = LinuxUser(u.get_linux_username(username_field=azure_ad_username_field))
        except Exception as e:
            logging.warning(f'Unable to create linux user object: {e}')
            continue

        # retrieve ssh keys for the linux user
        valid_keys = u.get_valid_ssh_keys(ssh_keys_suffix=ssh_keys_suffix, ssh_keys_prefix=ssh_keys_prefix)
        keys = [k for k in blobs if valid_keys.search(k.get('name', ''))]
        # if no keys are found in the storage account
        if not keys:
            logging.warning(f'No public ssh keys found for {getattr(u, "userPrincipalName", None)}')
        else:
            for k in keys:
                try:
                    lu.ssh_keys.append(azcontainer.download_blob(k.get('name')))
                except Exception as e:
                    lu.manage_ssh_keys = False
                    logging.warning(f'Unable to download ssh pub key {k}: {e}')

        # add linux user with valid username and ssh key to
        # linux users list
        linux_users.append(lu)

    # get local users in managed group
    managed_group_members = lxgroup.get_members()



    # verify local users against retrieved ad user objects
    # is the user enabled? # does the user exist in azure ad and locally?

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


