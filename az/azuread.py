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


    def get_group_members(self, group_id, additional_fields=[]):
        """
        retrieve a list of all azure ad group members and return
        a list of enabled azure users
        :param group_id:
        :return:
        """

        # default fields retrieved by the graph api
        # https://developer.microsoft.com/en-us/graph/docs/api-reference/v1.0/api/user_get?WT.mc_id=AZ-MVP-5003365#optional-query-parameters
        select = [
            'accountEnabled',
            'businessPhones',
            'displayName',
            'givenName',
            'id',
            'jobTitle',
            'mail',
            'mobilePhone',
            'officeLocation',
            'preferredLanguage',
            'surname',
            'userPrincipalName',
        ]
        # extend list with given additional fields
        select.extend(additional_fields)

        logging.debug(f'Retrieve group members for azure ad group {group_id}')
        # authorize request with the given token
        headers = {'Authorization': f'Bearer {self.graph_token}'}
        # select only certain fields from the user list
        params = {
            '$select': ','.join(select),
        }

        r = requests.get(
            url=f'https://graph.microsoft.com/v1.0/groups/{group_id}/members',
            headers=headers,
            params=params,
        )
        r.raise_for_status()

        # drop inactive accounts
        # filter queries arent supported for referenced properties (e.g. users in group)
        # so usingg $filter=accountEnabled eq true isnt working !
        # {"error":{"code":"Request_UnsupportedQuery","message":"The specified filter to the reference property query is currently not supported."
        members = []
        for m in r.json().get('value', []):
            if m.get('accountEnabled') == True:
                m.pop('@odata.type', None)
                members.append(m)

        if not members:
            raise ValueError(f'No members in group {group_id} found.')

        return members