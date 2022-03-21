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
    help="A space separated list of azure ad group ids to get users from",
    show_default=True,
    multiple=True
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
@click.option(
    '--additional-linux-groups',
    envvar='ADDITIONAL_LINUX_GROUPS',
    required=False,
    help="Space separated list of additional groups to join the managed accounts to.",
    show_default=True,
    multiple=True
)
def run(loglevel, tenant_id, client_id, client_secret,
        azure_ad_groups, azure_ad_username_field,
        storage_account_name, storage_account_container,
        ssh_keys_prefix, ssh_keys_suffix,
        linux_group_name, additional_linux_groups):
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
        azure_ad_users_to_linux_managed_group = LinuxGroup(name=linux_group_name)
        azure_ad_users_to_linux_managed_group.create()
    except Exception as e:
        logging.error(f'Unable to create linux group {linux_group_name}')
        raise e

    # retrieve azure ad users from the specified groups
    azure_ad_users = []
    for g in azure_ad_groups:
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
            lu = LinuxUser(username=u.get_linux_username(username_field=azure_ad_username_field))
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

    # first loop trough all linux users
    # create the user if it not exists
    # add the retrieved ssh keys
    # add user to additional user groups
    for u in linux_users:
        try:
            # check if the user already exists, if it exists make sure user is member in the managed group
            u.check_managed_user(managed_group=azure_ad_users_to_linux_managed_group.name)
            # create user if it doesnt exist
            u.create()
            # set authorized keys
            u.authorized_keys()
            # add user to groups
            u.group_memberships(managed_group=azure_ad_users_to_linux_managed_group.name, additional_groups=additional_linux_groups)
            # enable user login shell
            u.login_shell()
        except Exception as e:
            logging.warning(f'Unable to manage user {u.username}: {e}')

    # with the user managed and setup
    # get all users in the managed group
    linux_users_in_managed_group = []
    for u in azure_ad_users_to_linux_managed_group.get_members():
        linux_users_in_managed_group.append(LinuxUser(username=u))

    # pop all users which should be managed from the list
    # the remaining user accounts need to be disabled
    linux_users_in_managed_group_but_not_in_azure_ad = \
        [u for u in linux_users_in_managed_group if u.username not in [e.username for e in linux_users]]
    for u in linux_users_in_managed_group_but_not_in_azure_ad:
        logging.warning(f'Disabling user {u.username}')
        u.login_shell(login_shell='/sbin/nologin')


if __name__ == '__main__':
    try:
        run()
    except Exception as error:
        logging.error(error)
        sys.exit(1)


