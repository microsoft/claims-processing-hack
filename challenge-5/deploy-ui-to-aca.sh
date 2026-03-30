#!/usr/bin/env bash
# Deploy Claims Processing UI to Azure Container Apps
set -e

echo "🚀 Deploying Claims Processing API to Azure Container Apps"
echo "============================================================"

# Load environment variables
if [ ! -f ../.env ]; then
    echo "❌ Error: .env file not found. Please run Challenge 0 setup first."
    exit 1
fi

source ../.env

# Save current directory and navigate to workspace root for Docker build
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKSPACE_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Required variables
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP}"
ACR_NAME="${ACR_NAME}"
ENV_NAME="${CONTAINER_APP_ENVIRONMENT_NAME}"
APP_NAME="claims-processing-ui"

echo "==> Configuration (from .env):"
echo "    Resource Group: $RESOURCE_GROUP"
echo "    ACR:            $ACR_NAME"
echo "    Environment:    $ENV_NAME"

# Look up the API FQDN from the existing claims-processing-api container app
API_FQDN=$(az containerapp show --name claims-processing-api --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || true)
if [ -z "$API_FQDN" ]; then
  echo "Error: claims-processing-api not found in $RESOURCE_GROUP" >&2
  exit 1
fi
echo "    API FQDN:       $API_FQDN"

echo ""
echo "==> Building image in ACR..."
az acr build \
  --registry "$ACR_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image claims-ui:latest \
  "$SCRIPT_DIR" \
  --no-logs

echo "==> Deploying to Container Apps..."
# Update if app already exists, otherwise create
if az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
  echo "    Updating existing app: $APP_NAME"
  az containerapp update \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "${ACR_NAME}.azurecr.io/claims-ui:latest" \
    -o none
else
  echo "    Creating new app: $APP_NAME"
  az containerapp create \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$ENV_NAME" \
    --image "${ACR_NAME}.azurecr.io/claims-ui:latest" \
    --registry-server "${ACR_NAME}.azurecr.io" \
    --target-port 8501 \
    --ingress external \
    --env-vars "API_URL=https://${API_FQDN}" \
    -o none
fi

UI_FQDN=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

echo ""
echo "==> Streamlit UI deployed successfully!"
echo "    https://${UI_FQDN}"
