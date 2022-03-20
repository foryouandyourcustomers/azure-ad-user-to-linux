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