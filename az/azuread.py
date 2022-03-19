from azure.identity import ClientSecretCredential
import requests
import logging

class AzureAd(object):
    """
        simple azure ad client to retrieve group and user information from azure ad
    """

    def __init__(self, tenant_id, client_id, client_secret):
        self.credentials = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
           client_secret=client_secret
       )

        self.graph_token = self.credentials.get_token('https://graph.microsoft.com/.default').token


    def get_group_members(self, group_id):
        """
        retrieve a list of all azure ad group members and return
        :param group_id:
        :return:
        """

        logging.debug(f'Retrieve group members for azure ad group {group_id}')
        # authorize request with the given token
        headers = {'Authorization': f'Bearer {self.graph_token}'}
        # select only certain fields from the user list
        params = {
            '$select': 'id,displayName,mail,userPrincipalName,accountEnabled'
        }

        r = requests.get(
            url=f'https://graph.microsoft.com/v1.0/groups/{group_id}/members',
            headers=headers,
            params=params
        )
        r.raise_for_status()

        members = r.json().get('value', [])
        if not members:
            raise ValueError(f'No members in group {group_id} found.')

        return members