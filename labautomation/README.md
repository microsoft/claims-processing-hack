# Lab Automation

This directory contains the automation scripts and configuration for deploying the Claims Processing Hackathon to the Microsoft MicroHack platform.

## Files

- **deploy-lab.ps1** — PowerShell deployment script (entry point for MicroHack platform)
- **lab-defaults.json** — Lab configuration and metadata

## Platform Integration

This lab is configured for the **MicroHack EMEA platform** with the following parameters:

- **Deployment Type**: `resourcegroup` — Resources are deployed to a pre-created resource group
- **Deployment Locations**: `westeurope`, `swedencentral`, `norwayeast`, `northeurope`
- **Estimated Daily Cost**: ~$12.50 USD per user per day
- **Max Labs Per Subscription**: 4 concurrent labs

## How It Works

When deployed through the MicroHack platform:

1. The platform pre-creates an Azure resource group
2. The `deploy-lab.ps1` script is invoked with appropriate parameters
3. The script deploys all required Azure resources:
   - Storage Account (for data and artifacts)
   - Azure AI Foundry (for agents and models)
   - AI Search (for vectorized search)
   - Cosmos DB (for claims storage)
   - Container Registry (for Docker images)
   - Container Apps (for API server)
   - Application Insights (for monitoring)
   - Document Intelligence (for OCR)
   - Key Vault (for secrets)
   - API Management (for MCP server gateway)
4. Resource names are returned to the platform dashboard for easy access

## Architecture

The deployment provisions a complete enterprise AI stack for:
- **Document Processing**: Multiple OCR techniques (GPT-5.4 vision, Mistral AI, Azure Document Intelligence)
- **AI Agents**: Built with Microsoft Foundry for intelligent claims analysis
- **Vector Search**: AI Search integration for semantic search
- **MCP Server**: Deployment via Azure API Management for external AI assistants
- **Web Interface**: Streamlit UI for end-user interaction

## Resource Naming

Resources are named with the pattern: `msagthack-<resource-type>-<unique-suffix>`

The unique suffix is derived from the resource group ID to ensure deterministic naming across deployments.

## Cost Optimization

The deployment uses budget-conscious SKUs:
- AI Search: Basic tier
- Container Registry: Basic tier
- API Management: BasicV2 (1 unit)
- Cosmos DB: Serverless billing
- App Insights: Pay-as-you-go

## Manual Deployment (Outside MicroHack Platform)

If deploying outside the platform:

```powershell
az group create --name my-hackathon-rg --location westeurope

az deployment group create \
  --resource-group my-hackathon-rg \
  --template-file ../challenge-1/infra/azuredeploy.json \
  --parameters location=westeurope
```

## Support

For issues with the MicroHack platform integration, refer to the [microsoft/MicroHack repository](https://github.com/microsoft/MicroHack).

For issues with the lab content, see the main [README.md](../README.md).
