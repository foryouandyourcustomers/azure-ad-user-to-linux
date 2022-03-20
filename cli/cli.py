import subprocess
import logging


def _execute(cli):
    # rhel / centos 8 uses python3.6, so no capture_output for us
    #result = subprocess.run(cli, capture_output=True, text=True, shell=True)
    result = subprocess.run(cli, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    if result.stderr:
        raise ValueError(result.stderr)

    return result.stdout

class Cli(object):
    """
        execute different cli commands and parse their outputs
    """

    @staticmethod
    def getent(database, key):
        """
        execute getent and return the returned value
        https://man7.org/linux/man-pages/man1/getent.1.html

        :param database: database to query
        :param key: key to query for
        :return: string
        """

        return _execute(
            cli=f'/usr/bin/getent {database} {key}'
        )

    @staticmethod
    def groupadd(name):
        """
        create local linux group
        :param name:
        :return:
        """

        try:
            _execute(
                cli=f'/usr/sbin/groupadd --system {name}'
            )
        except ValueError as e:
            raise ValueError(f'Unable to create group {name}: {e}')

    @staticmethod
    def useradd(username):
        """
        create local linux user
        :param username:
        :return:
        """

        try:
            _execute(
                cli=f'/usr/sbin/useradd {username}'
            )
        except ValueError as e:
            raise ValueError(f'Unable to create user {username}: {e}')

    @staticmethod
    def joingroup(username, group):
        """
        join user to group
        :param username: name of the user to join
        :param group: name of the group to join
        :return:
        """

        try:
            _execute(
                cli=f'/usr/sbin/usermod -a -G {group} {username}'
            )
        except ValueError as e:
            raise ValueError(f'Unable to join user {username} to group {group}: {e}')