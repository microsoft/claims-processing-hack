#!/bin/bash
# Deploy Claims Processing API to Azure Container Apps
set -e

echo "🚀 Deploying Claims Processing API to Azure Container Apps"
echo "============================================================"

# Load environment variables
if [ ! -f ../.env ]; then
    echo "❌ Error: .env file not found. Please run Challenge 1 setup first."
    exit 1
fi

source ../.env

# Save current directory and navigate to workspace root for Docker build
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKSPACE_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Required variables
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP}"
ACR_NAME="${AZURE_CONTAINER_REGISTRY_NAME}"
ENVIRONMENT_NAME="${CONTAINER_APP_ENVIRONMENT_NAME}"
APP_NAME="claims-processing-api"
IMAGE_NAME="claims-processing-api"
IMAGE_TAG="latest"

echo ""
echo "📋 Deployment Configuration:"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   Container Registry: $ACR_NAME"
echo "   Container App Environment: $ENVIRONMENT_NAME"
echo "   App Name: $APP_NAME"
echo ""

# Step 1: Build Docker image
echo "🔨 Step 1: Building Docker image..."
cd "$WORKSPACE_ROOT"
docker build -f challenge-4/Dockerfile -t $IMAGE_NAME:$IMAGE_TAG .
cd "$SCRIPT_DIR"

# Step 2: Login to ACR
echo "🔐 Step 2: Logging in to Azure Container Registry..."
az acr login --name $ACR_NAME

# Step 3: Tag and push image
echo "📤 Step 3: Pushing image to ACR..."
docker tag $IMAGE_NAME:$IMAGE_TAG $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG
docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG

# Step 4: Verify Container App Environment exists (created in Challenge 1)
echo "🏗️  Step 4: Verifying Container App Environment..."
if ! az containerapp env show --name $ENVIRONMENT_NAME --resource-group $RESOURCE_GROUP &>/dev/null; then
    echo "   ❌ Error: Container App Environment not found: $ENVIRONMENT_NAME"
    echo "   Please run Challenge 1 deployment first to create the infrastructure."
    exit 1
else
    echo "   ✅ Environment exists: $ENVIRONMENT_NAME"
fi

# Step 5: Deploy Container App
echo "🚢 Step 5: Deploying Container App..."

# Check if app exists
if az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP &>/dev/null; then
    echo "   Updating existing app: $APP_NAME"
    az containerapp update \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --image $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG
else
    echo "   Creating new app: $APP_NAME"
    az containerapp create \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --environment $ENVIRONMENT_NAME \
        --image $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG \
        --target-port 8080 \
        --ingress external \
        --registry-server $ACR_NAME.azurecr.io \
        --cpu 1.0 \
        --memory 2.0Gi \
        --min-replicas 1 \
        --max-replicas 3 \
        --env-vars \
            AI_FOUNDRY_PROJECT_ENDPOINT="$AI_FOUNDRY_PROJECT_ENDPOINT" \
            MODEL_DEPLOYMENT_NAME="$MODEL_DEPLOYMENT_NAME" \
            MISTRAL_DOCUMENT_AI_ENDPOINT="$MISTRAL_DOCUMENT_AI_ENDPOINT" \
            MISTRAL_DOCUMENT_AI_KEY="$MISTRAL_DOCUMENT_AI_KEY" \
            MISTRAL_DOCUMENT_AI_DEPLOYMENT_NAME="$MISTRAL_DOCUMENT_AI_DEPLOYMENT_NAME"
fi

# Step 6: Enable managed identity (optional but recommended)
echo "🔑 Step 6: Enabling managed identity..."
az containerapp identity assign \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --system-assigned

PRINCIPAL_ID=$(az containerapp identity show \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query principalId -o tsv)

echo "   Granting Cognitive Services User role..."
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Cognitive Services User" \
    --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP" \
    2>/dev/null || echo "   Role assignment already exists"

# Step 7: Get app URL
echo ""
echo "✅ Deployment Complete!"
echo ""
APP_URL=$(az containerapp show \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn \
    -o tsv)

echo "🌐 Application URL: https://$APP_URL"
echo ""
echo "📊 View logs with:"
echo "   az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo ""
echo "🔍 Check status with:"
echo "   az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query properties.runningStatus"
echo ""
