#!/bin/bash
#
# This script will retrieve necessary keys and properties from Azure Resources 
# deployed using "Deploy to Azure" button and will store them in a file named
# ".env" in the parent directory.
#
# Two resource groups are used:
#   --resource-group  : contains general resources (storage, search, cosmos, doc intelligence, etc.)
#   RG_Foundry        : hardcoded resource group containing AI Foundry and OpenAI resources

# Login to Azure
if [ -z "$(az account show)" ]; then
  echo "User not signed in Azure. Signin to Azure using 'az login' command."
  az login --use-device-code
fi

# Get the resource group name from the script parameters
resourceGroupName=""
foundryResourceGroupName="RG_Foundry"

# Parse named parameters
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --resource-group) resourceGroupName="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Check if resourceGroupName is provided
if [ -z "$resourceGroupName" ]; then
    echo "Enter the resource group name where the general resources are deployed:"
    read resourceGroupName
fi

echo "Using foundry resource group: $foundryResourceGroupName"

# =====================================================================
# Get deployments from the GENERAL resource group
# =====================================================================
echo "Getting the deployments in general resource group '$resourceGroupName'..."
deploymentName=$(az deployment group list --resource-group $resourceGroupName --query "[?contains(name, 'Microsoft.Template') || contains(name, 'azuredeploy')].{name:name}[0].name" --output tsv)
if [ $? -ne 0 ]; then
    echo "Error occurred while fetching deployments from general resource group. Exiting..."
    exit 1
fi

echo "Getting the output parameters from the last deployment '$deploymentName' in '$resourceGroupName'..."
echo "Extracting the resource names from the deployment outputs..."
storageAccountName=$(az deployment group show --resource-group $resourceGroupName --name $deploymentName --query "properties.outputs.storageAccountName.value" -o tsv 2>/dev/null || echo "")
logAnalyticsWorkspaceName=$(az deployment group show --resource-group $resourceGroupName --name $deploymentName --query "properties.outputs.logAnalyticsWorkspaceName.value" -o tsv 2>/dev/null || echo "")
if [ -z "$logAnalyticsWorkspaceName" ]; then
    echo "Log Analytics workspace not found in deployment outputs, discovering by resource type..."
    logAnalyticsWorkspaceName=$(az monitor log-analytics workspace list --resource-group $resourceGroupName --query "[0].name" -o tsv 2>/dev/null || echo "")
fi
if [ -z "$logAnalyticsWorkspaceName" ]; then
    echo "No Log Analytics workspace found. Please enter the workspace name manually:"
    read logAnalyticsWorkspaceName
fi
logAnalyticsWorkspaceId=$(az monitor log-analytics workspace show --resource-group $resourceGroupName --workspace-name $logAnalyticsWorkspaceName --query customerId -o tsv 2>/dev/null || echo "")
searchServiceName=$(az deployment group show --resource-group $resourceGroupName --name $deploymentName --query "properties.outputs.searchServiceName.value" -o tsv 2>/dev/null || echo "")
keyVaultName=$(az deployment group show --resource-group $resourceGroupName --name $deploymentName --query "properties.outputs.keyVaultName.value" -o tsv 2>/dev/null || echo "")
containerRegistryName=$(az deployment group show --resource-group $resourceGroupName --name $deploymentName --query "properties.outputs.containerRegistryName.value" -o tsv 2>/dev/null || echo "")
applicationInsightsName=$(az deployment group show --resource-group $resourceGroupName --name $deploymentName --query "properties.outputs.applicationInsightsName.value" -o tsv 2>/dev/null || echo "")
documentIntelligenceName=$(az deployment group show --resource-group $resourceGroupName --name $deploymentName --query "properties.outputs.documentIntelligenceName.value" -o tsv 2>/dev/null || echo "")
apiManagementName=$(az deployment group show --resource-group $resourceGroupName --name $deploymentName --query "properties.outputs.apiManagementName.value" -o tsv 2>/dev/null || echo "")

# Extract endpoint URLs from general resource group
searchServiceEndpoint=$(az deployment group show --resource-group $resourceGroupName --name $deploymentName --query "properties.outputs.searchServiceEndpoint.value" -o tsv 2>/dev/null || echo "")
documentIntelligenceEndpoint=$(az deployment group show --resource-group $resourceGroupName --name $deploymentName --query "properties.outputs.documentIntelligenceEndpoint.value" -o tsv 2>/dev/null || echo "")
containerAppEnvironmentName=$(az deployment group show --resource-group $resourceGroupName --name $deploymentName --query "properties.outputs.containerAppEnvironmentName.value" -o tsv 2>/dev/null || echo "")
apiManagementGatewayUrl=$(az deployment group show --resource-group $resourceGroupName --name $deploymentName --query "properties.outputs.apiManagementGatewayUrl.value" -o tsv 2>/dev/null || echo "")

# =====================================================================
# Get deployments from the FOUNDRY resource group
# =====================================================================
echo ""
echo "Getting the deployments in foundry resource group '$foundryResourceGroupName'..."
foundryDeploymentName=$(az deployment group list --resource-group $foundryResourceGroupName --query "[?contains(name, 'Microsoft.Template') || contains(name, 'azuredeploy')].{name:name}[0].name" --output tsv)
if [ $? -ne 0 ]; then
    echo "Error occurred while fetching deployments from foundry resource group. Exiting..."
    exit 1
fi

echo "Getting the output parameters from the last deployment '$foundryDeploymentName' in '$foundryResourceGroupName'..."
echo "Extracting AI Foundry resource names from the foundry deployment outputs..."
aiFoundryHubName=$(az deployment group show --resource-group $foundryResourceGroupName --name $foundryDeploymentName --query "properties.outputs.aiFoundryHubName.value" -o tsv 2>/dev/null || echo "")
aiFoundryProjectName=$(az deployment group show --resource-group $foundryResourceGroupName --name $foundryDeploymentName --query "properties.outputs.aiFoundryProjectName.value" -o tsv 2>/dev/null || echo "")
aiFoundryHubEndpoint=$(az deployment group show --resource-group $foundryResourceGroupName --name $foundryDeploymentName --query "properties.outputs.aiFoundryHubEndpoint.value" -o tsv 2>/dev/null || echo "")
aiFoundryProjectEndpoint=$(az deployment group show --resource-group $foundryResourceGroupName --name $foundryDeploymentName --query "properties.outputs.aiFoundryProjectEndpoint.value" -o tsv 2>/dev/null || echo "")



# If deployment outputs are empty, try to discover resources by type in general RG
if [ -z "$storageAccountName" ] || [ -z "$logAnalyticsWorkspaceName" ] || [ -z "$apiManagementName" ] || [ -z "$keyVaultName" ] || [ -z "$containerRegistryName" ]; then
    echo "Some deployment outputs not found, discovering missing resources by type in general RG..."
    
    if [ -z "$storageAccountName" ]; then
        storageAccountName=$(az storage account list --resource-group $resourceGroupName --query "[0].name" -o tsv 2>/dev/null || echo "")
    fi
    
    if [ -z "$logAnalyticsWorkspaceName" ]; then
        logAnalyticsWorkspaceName=$(az monitor log-analytics workspace list --resource-group $resourceGroupName --query "[0].name" -o tsv 2>/dev/null || echo "")
    fi
    
    if [ -z "$searchServiceName" ]; then
        searchServiceName=$(az search service list --resource-group $resourceGroupName --query "[0].name" -o tsv 2>/dev/null || echo "")
    fi
    
    if [ -z "$apiManagementName" ]; then
        apiManagementName=$(az apim list --resource-group $resourceGroupName --query "[0].name" -o tsv 2>/dev/null || echo "")
    fi
    
    if [ -z "$keyVaultName" ]; then
        keyVaultName=$(az keyvault list --resource-group $resourceGroupName --query "[0].name" -o tsv 2>/dev/null || echo "")
    fi
    
    if [ -z "$containerRegistryName" ]; then
        containerRegistryName=$(az acr list --resource-group $resourceGroupName --query "[0].name" -o tsv 2>/dev/null || echo "")
    fi
    
    if [ -z "$applicationInsightsName" ]; then
        applicationInsightsName=$(az resource list --resource-group $resourceGroupName --resource-type "Microsoft.Insights/components" --query "[0].name" -o tsv 2>/dev/null || echo "")
    fi
    
    if [ -z "$documentIntelligenceName" ]; then
        documentIntelligenceName=$(az cognitiveservices account list --resource-group $resourceGroupName --query "[?kind=='FormRecognizer'].name | [0]" -o tsv 2>/dev/null || echo "")
    fi
fi

# If foundry deployment outputs are empty, try to discover AI Foundry resources in foundry RG
if [ -z "$aiFoundryHubName" ] || [ -z "$aiFoundryProjectName" ]; then
    echo "Some foundry deployment outputs not found, discovering AI Foundry resources in foundry RG..."
    
    if [ -z "$aiFoundryHubName" ]; then
        aiFoundryHubName=$(az cognitiveservices account list --resource-group $foundryResourceGroupName --query "[?kind=='AIServices'].name | [0]" -o tsv 2>/dev/null || echo "")
    fi
    
    if [ -z "$aiFoundryProjectName" ]; then
        echo "Discovering AI Foundry Project in foundry RG..."
        aiFoundryProjectName=$(az cognitiveservices account list --resource-group $foundryResourceGroupName --query "[?kind=='AIServicesProjectAccount' || kind=='OpenAI'].name | [0]" -o tsv 2>/dev/null || echo "")
        if [ -z "$aiFoundryProjectName" ]; then
            # Try to find project via ML workspace
            aiFoundryProjectName=$(az resource list --resource-group $foundryResourceGroupName --resource-type "Microsoft.MachineLearningServices/workspaces" --query "[?kind=='Project'].name | [0]" -o tsv 2>/dev/null || echo "")
        fi
    fi
fi

# Discover Container App Environment if not found in deployment outputs
if [ -z "$containerAppEnvironmentName" ]; then
    echo "Container App Environment not found in deployment outputs, discovering by resource type..."
    containerAppEnvironmentName=$(az resource list --resource-group $resourceGroupName --resource-type "Microsoft.App/managedEnvironments" --query "[0].name" -o tsv 2>/dev/null || echo "")
fi

# Get Cosmos DB service information (better retrieval)
echo "Getting Cosmos DB service information..."
cosmosDbAccountName=$(az deployment group show --resource-group $resourceGroupName --name $deploymentName --query "properties.outputs.cosmosDbAccountName.value" -o tsv 2>/dev/null || echo "")
if [ -z "$cosmosDbAccountName" ]; then
    cosmosDbAccountName=$(az cosmosdb list --resource-group $resourceGroupName --query "[0].name" -o tsv 2>/dev/null || echo "")
fi

if [ -n "$cosmosDbAccountName" ]; then
    cosmosDbEndpoint=$(az cosmosdb show --name $cosmosDbAccountName --resource-group $resourceGroupName --query documentEndpoint -o tsv 2>/dev/null || echo "")
    cosmosDbKey=$(az cosmosdb keys list --name $cosmosDbAccountName --resource-group $resourceGroupName --query primaryMasterKey -o tsv 2>/dev/null || echo "")
    
    # Construct the connection string properly
    if [ -n "$cosmosDbEndpoint" ] && [ -n "$cosmosDbKey" ]; then
        cosmosDbConnectionString="AccountEndpoint=${cosmosDbEndpoint};AccountKey=${cosmosDbKey};"
    else
        cosmosDbConnectionString=""
    fi
else
    echo "Warning: No Cosmos DB account found in resource group. You may need to deploy one."
    cosmosDbEndpoint=""
    cosmosDbKey=""
    cosmosDbConnectionString=""
fi

# Get the keys from the resources
echo "Getting the keys from the resources..."

# Storage account
if [ -n "$storageAccountName" ]; then
    storageAccountKey=$(az storage account keys list --account-name $storageAccountName --resource-group $resourceGroupName --query "[0].value" -o tsv 2>/dev/null || echo "")
    # Construct the connection string in the correct format
    storageAccountConnectionString="DefaultEndpointsProtocol=https;AccountName=${storageAccountName};AccountKey=${storageAccountKey};EndpointSuffix=core.windows.net"
else
    echo "Warning: Storage account not found"
    storageAccountKey=""
    storageAccountConnectionString=""
fi

# AI Foundry/Cognitive Services (from foundry resource group)
if [ -n "$aiFoundryHubName" ]; then
    aiFoundryEndpoint=$(az cognitiveservices account show --name $aiFoundryHubName --resource-group $foundryResourceGroupName --query properties.endpoint -o tsv 2>/dev/null || echo "")
    aiFoundryKey=$(az cognitiveservices account keys list --name $aiFoundryHubName --resource-group $foundryResourceGroupName --query key1 -o tsv 2>/dev/null || echo "")
else
    echo "Warning: AI Foundry Hub not found"
    aiFoundryEndpoint=""
    aiFoundryKey=""
fi

# Document Intelligence
if [ -n "$documentIntelligenceName" ]; then
    if [ -z "$documentIntelligenceEndpoint" ]; then
        documentIntelligenceEndpoint=$(az cognitiveservices account show --name $documentIntelligenceName --resource-group $resourceGroupName --query properties.endpoint -o tsv 2>/dev/null || echo "")
    fi
    documentIntelligenceKey=$(az cognitiveservices account keys list --name $documentIntelligenceName --resource-group $resourceGroupName --query key1 -o tsv 2>/dev/null || echo "")
else
    echo "Warning: Document Intelligence not found"
    documentIntelligenceEndpoint=""
    documentIntelligenceKey=""
fi

# Search service
if [ -n "$searchServiceName" ]; then
    searchServiceKey=$(az search admin-key show --resource-group $resourceGroupName --service-name $searchServiceName --query primaryKey -o tsv 2>/dev/null || echo "")
    if [ -z "$searchServiceEndpoint" ]; then
        searchServiceEndpoint="https://${searchServiceName}.search.windows.net"
    fi
else
    echo "Warning: Search service not found"
    searchServiceKey=""
    searchServiceEndpoint=""
fi

# API Management
if [ -n "$apiManagementName" ]; then
    if [ -z "$apiManagementGatewayUrl" ]; then
        apiManagementGatewayUrl=$(az apim show --name $apiManagementName --resource-group $resourceGroupName --query gatewayUrl -o tsv 2>/dev/null || echo "")
    fi
else
    echo "Warning: API Management not found"
    apiManagementGatewayUrl=""
fi

# Application Insights
if [ -n "$applicationInsightsName" ]; then
    appInsightsInstrumentationKey=$(az resource show --resource-group $resourceGroupName --name $applicationInsightsName --resource-type "Microsoft.Insights/components" --query properties.InstrumentationKey -o tsv 2>/dev/null || echo "")
else
    echo "Warning: Application Insights not found"
    appInsightsInstrumentationKey=""
fi

# Get Azure AI Search connection ID
# Note: The 'az cognitiveservices account connection' command is not available in all Azure CLI versions
# We'll construct the connection ID manually later in the script
echo "Skipping Azure AI Search connection query (will construct manually)..."
azureAIConnectionId=""

# Assign Azure AI Developer role to current user for AI Foundry agent management
echo ""
echo "=== Assigning Azure AI Developer role to current user ==="
echo "This role is required to create and manage AI Foundry agents."

# Get current user's object ID
currentUserObjectId=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || echo "")

if [ -n "$currentUserObjectId" ] && [ -n "$aiFoundryHubName" ]; then
    echo "Current user Object ID: $currentUserObjectId"
    
    # Get the AI Foundry Hub resource ID (from foundry resource group)
    aiFoundryResourceId=$(az cognitiveservices account show --name $aiFoundryHubName --resource-group $foundryResourceGroupName --query id -o tsv 2>/dev/null || echo "")
    
    if [ -n "$aiFoundryResourceId" ]; then
        # Check if user has permission to assign roles by attempting a dry-run list
        canAssignRoles=$(az role assignment list --scope "$aiFoundryResourceId" --query "[0]" -o tsv 2>/dev/null && echo "yes" || echo "no")
        
        if [ "$canAssignRoles" = "no" ]; then
            echo "⚠️  Insufficient permissions to assign roles. Skipping role assignments."
            echo "   Ask your admin to assign 'Azure AI Developer' and 'Cognitive Services User' roles to your account."
        else
            # Azure AI Developer role ID: 64702f94-c441-49e6-a78b-ef80e0188fee
            echo "Assigning 'Azure AI Developer' role..."
            az role assignment create \
                --assignee "$currentUserObjectId" \
                --role "64702f94-c441-49e6-a78b-ef80e0188fee" \
                --scope "$aiFoundryResourceId" \
                --only-show-errors 2>/dev/null && echo "✅ Azure AI Developer role assigned successfully" || echo "⚠️  Role may already exist or assignment failed (this is usually OK)"
            
            # Also assign Cognitive Services User role for additional access
            echo "Assigning 'Cognitive Services User' role..."
            az role assignment create \
                --assignee "$currentUserObjectId" \
                --role "a97b65f3-24c7-4388-baec-2e87135dc908" \
                --scope "$aiFoundryResourceId" \
                --only-show-errors 2>/dev/null && echo "✅ Cognitive Services User role assigned successfully" || echo "⚠️  Role may already exist or assignment failed (this is usually OK)"
        fi
    else
        echo "⚠️  Could not find AI Foundry Hub resource. Role assignment skipped."
    fi
else
    if [ -z "$currentUserObjectId" ]; then
        echo "⚠️  Could not determine current user's Object ID. Role assignment skipped."
        echo "   You may need to manually assign 'Azure AI Developer' role to access AI Foundry agents."
    fi
    if [ -z "$aiFoundryHubName" ]; then
        echo "⚠️  AI Foundry Hub not found. Role assignment skipped."
    fi
fi
echo ""

if [ -z "$storageAccountName" ] || [ -z "$aiFoundryProjectName" ]; then
    if [ -z "$storageAccountName" ]; then
        echo "Deployment outputs not found, discovering resources by type..."
        storageAccountName=$(az storage account list --resource-group $resourceGroupName --query "[0].name" -o tsv 2>/dev/null || echo "")
        searchServiceName=$(az search service list --resource-group $resourceGroupName --query "[0].name" -o tsv 2>/dev/null || echo "")
        applicationInsightsName=$(az resource list --resource-group $resourceGroupName --resource-type "Microsoft.Insights/components" --query "[0].name" -o tsv 2>/dev/null || echo "")
    fi
    if [ -z "$aiFoundryProjectName" ]; then
        echo "AI Foundry Project Name not found in deployment outputs, attempting discovery in foundry RG..."
        aiFoundryProjectName=$(az cognitiveservices account list --resource-group $foundryResourceGroupName --query "[?kind=='AIServicesProjectAccount' || kind=='OpenAI'].name | [0]" -o tsv 2>/dev/null || echo "")
        if [ -z "$aiFoundryProjectName" ]; then
            aiFoundryProjectName=$(az resource list --resource-group $foundryResourceGroupName --resource-type "Microsoft.MachineLearningServices/workspaces" --query "[?kind=='Project'].name | [0]" -o tsv 2>/dev/null || echo "")
        fi
    fi
    if [ -z "$aiFoundryHubName" ]; then
        aiFoundryHubName=$(az cognitiveservices account list --resource-group $foundryResourceGroupName --query "[?kind=='AIServices'].name | [0]" -o tsv 2>/dev/null || echo "")
    fi
fi

# Construct Azure AI Search connection ID directly
if [ -n "$aiFoundryHubName" ] && [ -n "$searchServiceName" ]; then
    echo "Constructing Azure AI Search connection ID..."
    
    # Get subscription ID
    subscriptionId=$(az account show --query id -o tsv 2>/dev/null || echo "")
    
    if [ -n "$subscriptionId" ]; then
        # Construct the connection ID based on the pattern: aiFoundryHubName + "-aisearch"
        # Pattern: /subscriptions/{subscription}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{aiFoundryHub}/connections/{aiFoundryHub}-aisearch
        azureAIConnectionId="/subscriptions/${subscriptionId}/resourceGroups/${foundryResourceGroupName}/providers/Microsoft.CognitiveServices/accounts/${aiFoundryHubName}/connections/${aiFoundryHubName}-aisearch"
        echo "Constructed connection ID: $azureAIConnectionId"
    else
        echo "Warning: Could not get subscription ID"
        azureAIConnectionId=""
    fi
else
    echo "Warning: Cannot construct Azure AI connection ID - AI Foundry Hub or Search Service not found"
    azureAIConnectionId=""
fi

# Construct AI Foundry Project Endpoint if not found in deployment outputs
if [ -z "$aiFoundryProjectEndpoint" ] && [ -n "$aiFoundryHubName" ] && [ -n "$aiFoundryProjectName" ]; then
    echo "Constructing AI Foundry Project Endpoint..."
    aiFoundryProjectEndpoint="https://${aiFoundryHubName}.services.ai.azure.com/api/projects/${aiFoundryProjectName}"
    echo "Constructed project endpoint: $aiFoundryProjectEndpoint"
elif [ -n "$aiFoundryProjectEndpoint" ] && [[ "$aiFoundryProjectEndpoint" == *"ai.azure.com/build/overview"* ]]; then
    # If we got a web UI URL from deployment outputs, convert it to API endpoint
    echo "Converting web UI URL to API endpoint..."
    aiFoundryProjectEndpoint="https://${aiFoundryHubName}.services.ai.azure.com/api/projects/${aiFoundryProjectName}"
    echo "Converted project endpoint: $aiFoundryProjectEndpoint"
fi

# Overwrite the existing .env file
if [ -f ../.env ]; then
    rm ../.env
fi

# Store the keys and properties in a file
echo "Storing the keys and properties in '.env' file..."

# Azure Storage (with both naming conventions)
echo "AZURE_STORAGE_ACCOUNT_NAME=\"$storageAccountName\"" >> ../.env
echo "AZURE_STORAGE_ACCOUNT_KEY=\"$storageAccountKey\"" >> ../.env
echo "AZURE_STORAGE_CONNECTION_STRING=\"$storageAccountConnectionString\"" >> ../.env

# Other Azure services
echo "LOG_ANALYTICS_WORKSPACE_NAME=\"$logAnalyticsWorkspaceName\"" >> ../.env
echo "SEARCH_SERVICE_NAME=\"$searchServiceName\"" >> ../.env
echo "SEARCH_SERVICE_ENDPOINT=\"$searchServiceEndpoint\"" >> ../.env
echo "SEARCH_ADMIN_KEY=\"$searchServiceKey\"" >> ../.env
echo "AI_FOUNDRY_HUB_NAME=\"$aiFoundryHubName\"" >> ../.env
echo "AI_FOUNDRY_PROJECT_NAME=\"$aiFoundryProjectName\"" >> ../.env
echo "AI_FOUNDRY_ENDPOINT=\"$aiFoundryEndpoint\"" >> ../.env
echo "AI_FOUNDRY_KEY=\"$aiFoundryKey\"" >> ../.env
acr_username=$(az acr credential show --name $containerRegistryName --query username -o tsv)
acr_password=$(az acr credential show --name $containerRegistryName --query passwords[0].value -o tsv)
# Construct AI Foundry Hub Endpoint if missing
if [ -z "$aiFoundryHubEndpoint" ] && [ -n "$aiFoundryHubName" ]; then
    echo "Constructing AI Foundry Hub Endpoint..."
    subscriptionId=$(az account show --query id -o tsv 2>/dev/null || echo "")
    if [ -n "$subscriptionId" ]; then
        aiFoundryHubEndpoint="https://ml.azure.com/home?wsid=/subscriptions/${subscriptionId}/resourceGroups/${foundryResourceGroupName}/providers/Microsoft.CognitiveServices/accounts/${aiFoundryHubName}"
        echo "Constructed hub endpoint: $aiFoundryHubEndpoint"
    fi
fi
echo "AI_FOUNDRY_HUB_ENDPOINT=\"$aiFoundryHubEndpoint\"" >> ../.env

# Construct AI Foundry Project Endpoint if not found in deployment outputs
if [ -z "$aiFoundryProjectEndpoint" ] && [ -n "$aiFoundryHubName" ] && [ -n "$aiFoundryProjectName" ]; then
    echo "Constructing AI Foundry Project Endpoint..."
    aiFoundryProjectEndpoint="https://${aiFoundryHubName}.services.ai.azure.com/api/projects/${aiFoundryProjectName}"
    echo "Constructed project endpoint: $aiFoundryProjectEndpoint"
elif [ -n "$aiFoundryProjectEndpoint" ] && [[ "$aiFoundryProjectEndpoint" == *"ai.azure.com/build/overview"* ]]; then
    # If we got a web UI URL from deployment outputs, convert it to API endpoint
    echo "Converting web UI URL to API endpoint..."
    aiFoundryProjectEndpoint="https://${aiFoundryHubName}.services.ai.azure.com/api/projects/${aiFoundryProjectName}"
    echo "Converted project endpoint: $aiFoundryProjectEndpoint"
fi
echo "AI_FOUNDRY_PROJECT_ENDPOINT=\"$aiFoundryProjectEndpoint\"" >> ../.env
echo "AZURE_AI_CONNECTION_ID=\"$azureAIConnectionId\"" >> ../.env
# Azure Cosmos DB
echo "COSMOS_ENDPOINT=\"$cosmosDbEndpoint\"" >> ../.env
echo "COSMOS_KEY=\"$cosmosDbKey\"" >> ../.env
echo "COSMOS_CONNECTION_STRING=\"$cosmosDbConnectionString\"" >> ../.env

# For backward compatibility, also set OpenAI-style variables pointing to AI Foundry
echo "AZURE_OPENAI_SERVICE_NAME=\"$aiFoundryHubName\"" >> ../.env
echo "AZURE_OPENAI_ENDPOINT=\"$aiFoundryEndpoint\"" >> ../.env
echo "AZURE_OPENAI_KEY=\"$aiFoundryKey\"" >> ../.env
echo "AZURE_OPENAI_DEPLOYMENT_NAME=\"gpt-4.1-mini\"" >> ../.env
echo "AZURE_OPENAI_API_VERSION=\"2024-12-01-preview\"" >> ../.env
echo "MODEL_DEPLOYMENT_NAME=\"gpt-4.1-mini\"" >> ../.env

# Mistral Document AI deployment
echo "MISTRAL_DOCUMENT_AI_DEPLOYMENT_NAME=\"mistral-document-ai-2505\"" >> ../.env
echo "MISTRAL_DOCUMENT_AI_ENDPOINT=\"$aiFoundryEndpoint\"" >> ../.env
echo "MISTRAL_DOCUMENT_AI_KEY=\"$aiFoundryKey\"" >> ../.env

# Document Intelligence
echo "DOCUMENT_INTELLIGENCE_ENDPOINT=\"$documentIntelligenceEndpoint\"" >> ../.env
echo "DOCUMENT_INTELLIGENCE_KEY=\"$documentIntelligenceKey\"" >> ../.env

# Container Apps
echo "CONTAINER_APP_ENVIRONMENT_NAME=\"$containerAppEnvironmentName\"" >> ../.env

# Resource Group  
echo "AZURE_RESOURCE_GROUP=\"$resourceGroupName\"" >> ../.env
echo "AZURE_FOUNDRY_RESOURCE_GROUP=\"$foundryResourceGroupName\"" >> ../.env

# API Management
echo "API_MANAGEMENT_NAME=\"$apiManagementName\"" >> ../.env
echo "API_MANAGEMENT_GATEWAY_URL=\"$apiManagementGatewayUrl\"" >> ../.env

# Container Registry (with both naming conventions)
echo "ACR_NAME=\"$containerRegistryName\"" >> ../.env
echo "AZURE_CONTAINER_REGISTRY_NAME=\"$containerRegistryName\"" >> ../.env
echo "ACR_USERNAME=\"$acr_username\"" >> ../.env
echo "ACR_PASSWORD=\"$acr_password\"" >> ../.env

echo "Keys and properties are stored in '.env' file successfully."

# Display summary of what was configured
echo ""
echo "=== Configuration Summary ==="
echo "General Resource Group: $resourceGroupName"
echo "Foundry Resource Group: $foundryResourceGroupName"
echo "Storage Account: $storageAccountName"
echo "Log Analytics Workspace: $logAnalyticsWorkspaceName"
echo "Search Service: $searchServiceName"
echo "API Management: $apiManagementName"
echo "AI Foundry Hub: $aiFoundryHubName (from $foundryResourceGroupName)"
echo "AI Foundry Project: $aiFoundryProjectName (from $foundryResourceGroupName)"
echo "Key Vault: $keyVaultName"
echo "Container Registry: $containerRegistryName"
echo "Application Insights: $applicationInsightsName"
echo "Container App Environment: $containerAppEnvironmentName"
echo "Document Intelligence: $documentIntelligenceName"

if [ -n "$cosmosDbAccountName" ]; then
    echo "Cosmos DB: $cosmosDbAccountName"
else
    echo "Cosmos DB: NOT FOUND - You may need to deploy this service"
fi
echo "Environment file created: ../.env"

# Show what needs to be deployed
missing_services=""
if [ -z "$storageAccountName" ]; then missing_services="$missing_services Storage"; fi
if [ -z "$searchServiceName" ]; then missing_services="$missing_services Search"; fi
if [ -z "$aiFoundryHubName" ]; then missing_services="$missing_services AI-Foundry"; fi

if [ -n "$missing_services" ]; then
    echo ""
    echo "⚠️  Missing services:$missing_services"
    echo "You may need to deploy these services manually or check your deployment template."
fi