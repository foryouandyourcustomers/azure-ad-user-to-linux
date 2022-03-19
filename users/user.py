import logging
import re

def sort_users_unique(users, sort_key='mail', unique_key='id'):
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


class User(object):
    """
        represent a user account - data is a mix of user information retrieved
        from azure ad and the local linux system
    """

    def __init__(self, id, displayName, mail, userPrincipalName, accountEnabled, ssh_keys_prefix, ssh_keys_suffix, **args):
        """
            initialize user object. the constructor is called
            from the dictionary returned by the member list retrieved
            by the azuread client
        """

        self.id = id
        self.display_name = displayName
        self.mail = mail
        self.user_principal_name = userPrincipalName
        self.account_enabled = accountEnabled

        if ssh_keys_prefix:
            self.valid_ssh_keys = re.compile(f'({ssh_keys_prefix})?{self.user_principal_name}(\.[a-zA-Z0-9-._]*?)?{ssh_keys_suffix}')
        else:
            self.valid_ssh_keys = re.compile(f'{self.user_principal_name}(\.[a-zA-Z0-9-._]*?.)?{ssh_keys_suffix}')

        self.ssh_keys = []