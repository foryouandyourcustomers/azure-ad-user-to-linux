from cli import Cli
import logging

class LinuxGroup(object):
    """
        represent a local linux user group
    """

    def __init__(self, name):
        """
        initialize the group object
        :param name:
        """
        self.name = name


    def exists(self):
        """
        return true or false if the group exists or not
        :return:
        """

        if Cli.getent(database='group', key=self.name):
            return True
        else:
            return False

    def create(self):
        """
        create group
        :return:
        """

        if not self.exists():
            logging.info(f'Create linux group {self.name}')
            Cli.groupadd(name=self.name)


    def getent(self):
        """
        returns the split getent for the group database entry

        :return: getent list
        """

        group_entry = Cli.getent(database='group', key=self.name)
        if group_entry:
            # split group entry 'group:x:id:members'
            return group_entry.decode().strip().split(':')
        return None

    def get_id(self):
        """
        returns the id of the group
        :return: id of group
        """

        g = self.getent()
        if g:
            return g[2]
        return None


    def get_members(self):
        """
        returns the list
        :return: list of members
        """

        g = self.getent()
        if g:
            return g[3].split(',')
        return None
