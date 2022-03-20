from cli import Cli
import logging
import os

class LinuxUser(object):
    """
    represent a local linux user
    """

    def __init__(self, username):
        """
        initialize the linux user object
        :param username:
        """
        self.username = username
        self.ssh_keys = []
        self.manage_ssh_keys = True

    def exists(self):
        """
        return true or false if the user exists or not
        :return:
        """

        if Cli.getent(database='passwd', key=self.username):
            return True
        else:
            return False

    def create(self):
        """
        create user
        :return:
        """

        if not self.exists():
            logging.info(f'Create linux user {self.username}')
            Cli.useradd(username=self.username)

    def getent(self):
        """
        returns the split getent for the passwd database entry

        :return: getent list
        """

        passwd_entry = Cli.getent(database='passwd', key=self.username)
        if passwd_entry:
            # split passwd entry 'login:x:uid:gid::homedir:loginshell'
            return passwd_entry.decode().strip().split(':')
        return None

    def get_home(self):
        """
        returns the home directory of the user
        :return: id of group
        """

        p = self.getent()
        if p:
            return p[5]
        return None


    def get_uid(self):
        """
        returns the uid of the user
        :return: id of group
        """

        p = self.getent()
        if p:
            return int(p[2])
        return None

    def get_gid(self):
        """
        returns the gid of the user
        :return: id of group
        """

        p = self.getent()
        if p:
            return int(p[3])
        return None


    def authorized_keys(self,
                        authorized_keys_file='.ssh/authorized_keys',
                        authorized_keys_comment='managed by azure-ad-user-to-linux'):
        """
        manage authorized keys file
        :return:
        """

        if not self.manage_ssh_keys:
            logging.warning(f'Unable to manage ssh keys for user {self.username}')
            return

        # setup full path to the authorized keys file
        authorized_keys = os.path.join(self.get_home(), authorized_keys_file)

        # make sure the auth to the authorized keys file exists
        os.makedirs(
            name=os.path.dirname(authorized_keys),
            mode=0o0755,
            exist_ok=True
        )

        # make sure ownership of the folder are correct
        os.chown(
            path=os.path.dirname(authorized_keys),
            uid=self.get_uid(),
            gid=self.get_gid(),
        )

        # now get the authorized keys file,
        # if it exists load the ssh keys
        current_authorized_keys = []
        if os.path.isfile(authorized_keys):
            with open(authorized_keys) as file:
                # load all lines but drop all the previously managed ssh keys - identified by the comment
                for line in file:
                    l = line.strip()
                    if l and not l.endswith(authorized_keys_comment):
                        current_authorized_keys.append(l)

        # (re)add the ssh public keys retrieved from the storage account
        for key in self.ssh_keys:
            current_authorized_keys.append(f'{key} {authorized_keys_comment}')

        # overwrite authorized keys file with new list
        with open(authorized_keys, 'w') as file:
            for l in current_authorized_keys:
                file.write(f'{l}\n')

        # and ensure ownership and permission of the file is correct
        os.chown(
            path=authorized_keys,
            uid=self.get_uid(),
            gid=self.get_gid(),
        )
        os.chmod(
            path=authorized_keys,
            mode=0o0644
        )

    def group_memberships(self, groups):
        """
        join the user account to additional linux groups
        the function only adds users to groups, never removes them

        :param groups: list of groups to join users too
        :return:
        """

        for g in groups:
            try:
                Cli.joingroup(self.username, g)
            except Exception as e:
                logging.warning(e)

