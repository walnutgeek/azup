# Import the needed credential and management objects from the libraries.
from azure.mgmt.resource import ResourceManagementClient
from azure.identity import AzureCliCredential
import os
def create_rg(sub_id, rg_name):
    # Acquire a credential object using CLI-based authentication.
    credential = AzureCliCredential()

    # Obtain the management object for resources.
    resource_client = ResourceManagementClient(credential, sub_id)

    location = "eastus2"
    # Provision the resource group.
    rg_result = resource_client.resource_groups.create_or_update(
        rg_name,
        {
            "location": location
        }
    )

    # Within the ResourceManagementClient is an object named resource_groups,
    # which is of class ResourceGroupsOperations, which contains methods like
    # create_or_update.
    #
    # The second parameter to create_or_update here is technically a ResourceGroup
    # object. You can create the object directly using ResourceGroup(location=LOCATION)
    # or you can express the object as inline JSON as shown here. For details,
    # see Inline JSON pattern for object arguments at
    # https://docs.microsoft.com/azure/developer/python/azure-sdk-overview#inline-json-pattern-for-object-arguments.

    print(f"Provisioned resource group {rg_result.name} in the {rg_result.location} region")

    # The return value is another ResourceGroup object with all the details of the
    # new group. In this case the call is synchronous: the resource group has been
    # provisioned by the time the call returns.

    # To update the resource group, repeat the call with different properties, such
    # as tags:
    rg_result = resource_client.resource_groups.create_or_update(
        rg_name,
        {
            "location": location,
            "tags": { "environment":"test", "department":"tech" }
        }
    )

    print(f"Updated resource group {rg_result.name} with tags")

    # Optional lines to delete the resource group. begin_delete is asynchronous.
    # poller = resource_client.resource_groups.begin_delete(rg_result.name)
    # result = poller.result()