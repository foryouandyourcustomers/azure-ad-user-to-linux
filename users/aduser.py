import logging
import re

def sort_ad_users_unique(users, sort_key='mail', unique_key='id'):
    """
    sort given list of user objects and returns a sorted and unique list of objects
    :param users: list of user objects
    :return: sorted, unique list
    """

    # loop over the given users list and drop non unique
    # entries
    users_unique = []
    for u in users:
        is_duplicate = False
        for uu in users_unique:
            if getattr(u, unique_key) == getattr(uu, unique_key):
                is_duplicate = True
                break

        if not is_duplicate:
            users_unique.append(u)

    # return sorted list of user objects
    return sorted(users_unique, key=lambda a: getattr(a, sort_key))


class AdUser(object):
    """
        represent a user account - data is a mix of user information retrieved
        from azure ad and the local linux system
    """

    def __init__(self, **kwargs):
        """
            initialize user object. the constructor is called
            from the dictionary returned by the member list retrieved
            by the azuread client
        """

        # load all retrieved values from azure graph as attributes
        for k,v in kwargs.items():
            setattr(self, k, v)

    def get_valid_ssh_keys(self, ssh_keys_prefix, ssh_keys_suffix):
        """
        :param ssh_keys_prefix: prefix for ssh key files in the storage account
        :param ssh_keys_suffix: suffix for ssh key files in the storage account
        :return:
        """

        if not getattr(self, 'userPrincipalName'):
            raise ValueError('No userPrinicipalName set. unable to create ssh key name for user')

        regexp = f'{getattr(self, "userPrincipalName")}(\.[a-zA-Z0-9-._]*?.)?{ssh_keys_suffix}'
        if ssh_keys_prefix:
            regexp = f'({ssh_keys_prefix})?{regexp}'
        return re.compile(regexp)

    def get_linux_username(self, username_field):
        """
        create a valid linux username from the value in the username field
        :param username_field: name of the field containing the value for the username
        :return: string with valid linux username
        """

        username_value = getattr(self, username_field, None)
        if not username_value:
            raise ValueError(f'Unable to get value for linux username from field {username_field}')

        # create a valid linux username from the given string
        # in most cases userPrincipalName will be used, and in most cases this will be a email address
        # therefore remove everything after the @ sign
        # then convert everything to lowercase,
        # replace dots and dashaes with _
        # cut string at 31 chars
        username_value = username_value.split('@')[0]
        username_value = username_value.lower()
        username_value = username_value.replace('.', '_')
        username_value = username_value.replace('-', '_')
        username_value = username_value[:31]

        return username_value
