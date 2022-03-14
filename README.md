# azure-ad-user-to-linux

We don't want to administer our own user accounts on linux servers. Instead, we want to leverage
Azure AD for the account management.

As there is no daemon or service which works out of the box for non Azure VMs and Linux Servers which aren't members
of an AD we need to get creative.

The elegant way would be to create our own pam.d modules but this makes everything more complicated than
it needs to be. Instead, we use a simple script to retrieve Azure AD accounts and public keys and manage the 
local users accordingly.

## Overview

The script is executed as cronjob on each linux server (or it can be executed manually)

1) It retrieves all users which are members of one or more AD groups
2) It checks if the user accounts retrieved from AD exist on the linux server. It compares the AD username with all local
user accounts in a specific linux group. This group check is so we don't disable users which were never synced
from azure ad!
   1) If the user exist it verifies if the user is enabled in AD, if not it sets the users login shell to `nologin`
   2) If the user doesnt exist it will create it with the information from the Azure AD user.
3) It retrieves SSH public keys stored as text file (one public key, one text file) from the specified azure storage account container
   1) the container uses a simple folder structure `/<userPrincipalName>/key1.txt`, `/<userPrincipalName>/key2.txt`
4) It checks if the retrieved ssh public key exists in the users `authorized_keys` file.
   1) if it doesnt exist add it
   2) if there are further managed ssh keys which aren't in the storage account remove them. It verifies if the key is managed by the script by checking the keys comment

## Requirements
 
- Administrative rights in Azure 
- (optional) azure cli installed - the cli is used to create the application registration etc. Alternatively, the preparation steps can be executed via the Azure webinterface.

## Preparation in Azure

The following steps need to be executed in Azure to make the script ready for use.

### Create a resource group

```bash
# make sure we are working in the correct subscription
az account set --subscription mysubscription
# create a resource group for the storage account
az group create --location switzerlandnorth --name azure-ad-user-to-linux
```

### Create a storage account

The storage account will store the users public keys.

```bash
# create a storage account for the ssh public keys
az storage account create --resource-group azure-ad-user-to-linux --name aadusertolinuxconfig
# create a container to upload and download the ssh keys from
az storage container create --account-name aadusertolinuxconfig --name ssh-keys
```

### Create an Application Registration

```bash
# create a service principal (application registration) with read access to the storage account
# and a password valid for the next 100 years
az ad sp create-for-rbac \
    --name "azure-ad-user-to-linux" \
    --years 100 \
    --role "Storage Blob Data Reader" \
    --scopes "/subscriptions/mysubscription/resourceGroups/azure-ad-user-to-linux/providers/Microsoft.Storage/storageAccounts/aadusertolinuxconfig"
```

The command will print a json output. Please store the appId (username) and the password somewhere safe.
You won't be able to retrieve the password afterwards!

```json
{
  "appId": "7307b99d-b5a2-4ee7-b947-2fe8944baccf",
  "displayName": "azure-ad-user-to-linux",
  "name": "7307b99d-b5a2-4ee7-b947-2fe8944baccf",
  "password": "... snip ...",
  "tenant": "mytenant"
}
```

Next, we need to grant the service principal access to the Azure AD graph.
The service principal requires 'User.Read.All' and 'Group.Read.All' permissions for Azure Graph.

```bash
# add user.read.all permissions
# --api: the id of the azure graph api
# --api-permission: the id of the user.read.all permission, the =Role at the end allows application permissions. 
# --id: the id of the application created in the last step
az ad app permission add \
    --api 00000003-0000-0000-c000-000000000000 \
    --api-permission df021288-bdef-4463-88db-98f22de89214=Role \
    --id 7307b99d-b5a2-4ee7-b947-2fe8944baccf
    
# add group.read.all permissions
az ad app permission add \
    --api 00000003-0000-0000-c000-000000000000 \
    --api-permission 5b567255-7703-4780-807c-7be8301ae99b=Role \
    --id 7307b99d-b5a2-4ee7-b947-2fe8944baccf

# grant admin consent for the permissions
az ad app permission admin-consent --id 7307b99d-b5a2-4ee7-b947-2fe8944baccf

```

The application needs admin consent for the permissions as it is running as "application" and not on behalf of a 
logged in user.

## Installation

tbd.

## Usage

## Limitations

- The script currently only works with password authentication for the Azure Application Registration (service principal)
- The script assumes the authorized key file is `${HOME}/.ssh/authorized_keys`