from azure.storage.blob import ContainerClient
from azure.identity import ClientSecretCredential
import logging

class AzureContainer(object):
    """
        represent an azure blob container, used to download ssh keys
    """

    def __init__(self, tenant_id, client_id, client_secret, storage_account_name, storage_account_container):
        self.credentials = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )

        self.account_url = f'https://{storage_account_name}.blob.core.windows.net'
        self.container = storage_account_container
        self.client = ContainerClient(
            account_url=self.account_url,
            container_name=self.container,
            credential=self.credentials
        )

    def get_blobs(self, prefix=None, suffix=None):
        """
        return a list of all blobs. if prefix is specified, return only blobs starting with the prefix.


        :param prefix:
        :return: list of found blobs with name and last modified date
        """
        logging.debug(f'Retrieve blobs from {self.account_url}/{self.container}')
        blobs = self.client.list_blobs(name_starts_with=prefix)

        returned_blobs = []
        for b in blobs:
            if b.get('name').endswith(suffix):
                returned_blobs.append({'name': b.get('name'), 'last_modified': b.get('last_modified')})

        if not returned_blobs:
            raise ValueError(f'No blobs found with prefix {prefix} and suffix {suffix} in {self.account_url}/{self.container}')

        return returned_blobs

    def download_blob(self, name):
        """
        download the specified blob

        :param name: name of the blob to download
        :return: string
        """
        logging.debug(f'Download blob {self.account_url}/{self.container}/{name}')
        download = self.client.download_blob(name).readall()

        return download.decode().strip()
