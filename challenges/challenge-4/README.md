# Challenge 4: Multi-Agent Workflow and API Deployment

**Expected Duration:** 60 minutes

## Introduction

Welcome to Challenge 4! In this challenge, you'll orchestrate the two specialized agents you built in Challenge 3 (OCR Agent and JSON Structuring Agent) into a cohesive workflow. You'll then deploy this multi-agent workflow as a **REST API** to Azure Container Apps, making your claims processing system accessible as a cloud service that can be consumed by any application via HTTP requests.

## What are we building?

In this challenge, you will create:

- **Multi-Agent Workflow**: Orchestrate the OCR Agent and JSON Structuring Agent into a sequential processing pipeline
- **REST API Server**: FastAPI-based service exposing the workflow through HTTP endpoints
- **Cloud Deployment**: Deploy the API to Azure Container Apps with auto-scaling
- **Integration Testing**: Comprehensive test suite for local and deployed validation

## Architecture Overview

```
┌──────────────┐
│    Client    │
│  (Any HTTP)  │
└──────┬───────┘
       │
       │ POST /process-claim/upload
       │
┌──────▼────────────────────────────────┐
│   Azure Container App                  │
│                                        │
│  ┌──────────────────────────────┐    │
│  │     FastAPI Server           │    │
│  │  (api_server.py)             │    │
│  └──────────┬───────────────────┘    │
│             │                         │
│  ┌──────────▼───────────────────┐    │
│  │  Workflow Orchestrator       │    │
│  │  (workflow_orchestrator.py)  │    │
│  └──────────┬───────────────────┘    │
│             │                         │
│      ┌──────┴──────┐                 │
│      │             │                 │
│  ┌───▼────┐   ┌───▼─────────┐       │
│  │  OCR   │   │   JSON      │       │
│  │ Agent  │──▶│ Structure   │       │
│  └────────┘   │   Agent     │       │
│               └─────────────┘       │
└────────────────────────────────────┘
```

## Understanding the Architecture

The solution combines two specialized AI agents from Challenge 3 into a REST API:

1. **OCR Agent** → Extracts text from claim images (Mistral Document AI)
2. **JSON Structuring Agent** → Converts text to structured data (Azure AI Foundry)
3. **FastAPI Server** → Exposes endpoints for file upload and base64 processing
4. **Azure Container Apps** → Hosts the API with auto-scaling and managed identity

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/process-claim/upload` | POST | Process image via file upload |
| `/process-claim/base64` | POST | Process image via base64 encoding |

See [`api_server.py`](api_server.py) for implementation details.


## Tasks

### Task 1: Understand the Workflow Implementation

#### 1.1 Review the Workflow Orchestrator

Open and review [`workflow_orchestrator.py`](workflow_orchestrator.py):

**Key Components**:
- `process_claim_workflow()`: Main async function that orchestrates the agents
- **Step 1**: OCR Agent extracts text from the image
- **Step 2**: JSON Structuring Agent converts text to structured JSON
- Error handling for each step
- Metadata tracking (source image, character count, workflow type)

See [`workflow_orchestrator.py`](workflow_orchestrator.py) for the complete implementation.

#### 1.2 Test the Workflow

Install dependencies and test the workflow:

```bash
cd challenge-4

# Install Python dependencies
pip install -r requirements.txt

# Test the workflow with a sample image
python workflow_orchestrator.py ../challenge-1/data/statements/crash1_front.jpeg
```

### Task 2: Review and Test the API Server

#### 2.1 Review the FastAPI Implementation

Open and review [`api_server.py`](api_server.py):

**Key Components**:
- **FastAPI app** with health and processing endpoints
- **Request/Response models** using Pydantic
- **File upload handler** with temporary file management
- **Base64 handler** for JSON-based requests
- **Error handling** with proper HTTP status codes
- **Async processing** for better performance

See [`api_server.py`](api_server.py) for the complete implementation of all endpoints.

#### 2.2 Start the API Server Locally

```bash
# Make sure you're in challenge-4 directory
cd challenge-4

# Start the API server
python api_server.py
```

The server will start on `http://localhost:8080`

#### 2.2 Test with Python Client

```bash
# Run the comprehensive Python test suite
python test_api_client.py

# Or use the bash end-to-end test (no Python dependencies)
./test_e2e.sh
```

### Task 3: Build and Test Docker Container

#### 3.1 Review the Dockerfile

Open and review [`Dockerfile`](Dockerfile):

**Key aspects**:
- Uses Python 3.11 slim base image
- Installs dependencies from `requirements.txt`
- Copies application files and OCR agent scripts
- Exposes port 8080
- Runs `api_server.py` as the entrypoint

#### 3.2 Build the Docker Image

```bash
# Build the Docker image from workspace root
cd /workspaces/claims-processing-hack
docker build -f challenge-4/Dockerfile -t claims-processing-api:latest .
```

#### 3.3 Test Locally with Docker

```bash
# Load environment variables (from workspace root)
cd /workspaces/claims-processing-hack
source .env

# Run the container
docker run -p 8080:8080 \
  -e AI_FOUNDRY_PROJECT_ENDPOINT="$AI_FOUNDRY_PROJECT_ENDPOINT" \
  -e MODEL_DEPLOYMENT_NAME="$MODEL_DEPLOYMENT_NAME" \
  -e MISTRAL_DOCUMENT_AI_ENDPOINT="$MISTRAL_DOCUMENT_AI_ENDPOINT" \
  -e MISTRAL_DOCUMENT_AI_KEY="$MISTRAL_DOCUMENT_AI_KEY" \
  -e MISTRAL_DOCUMENT_AI_DEPLOYMENT_NAME="$MISTRAL_DOCUMENT_AI_DEPLOYMENT_NAME" \
  claims-processing-api:latest

# Test in another terminal
curl http://localhost:8080/health
```

### Task 4: Deploy to Azure Container Apps

#### 4.1 Review the Deployment Script

Open and review [`deploy-to-azure.sh`](deploy-to-azure.sh):

**What it does**:
1. Loads environment variables from `.env`
2. Builds Docker image
3. Logs into Azure Container Registry
4. Tags and pushes image to ACR
5. Deploys to Azure Container Apps with:
   - External HTTPS ingress
   - Environment variables
   - Auto-scaling (1-3 replicas)
   - 1 CPU, 2GB memory per replica
6. Enables managed identity
7. Assigns Cognitive Services User role
8. Displays the application URL

#### 4.2 Deploy Using the Script

```bash
# Navigate to challenge-4 directory
cd challenge-4

# Make script executable (if not already)
chmod +x deploy-to-azure.sh

# Run deployment (script will automatically use workspace root for Docker build)
./deploy-to-azure.sh
```

### Task 5: Test the Deployed API

#### 5.1 Get Your API URL

```bash
# Get the application URL
APP_URL=$(az containerapp show \
  --name claims-processing-api \
  --resource-group $AZURE_RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  -o tsv)

echo "API URL: https://$APP_URL"
```

#### 5.2 Test with curl

```bash
# Test health endpoint
curl https://$APP_URL/health

# Test claim processing
curl -X POST https://$APP_URL/process-claim/upload \
  -F "file=@../challenge-1/data/statements/crash1_front.jpeg" \
  | jq .
```


### Task 6: Test Your API in Azure API Management (APIM)

In this task, we'll use our existing API (already deployed to Azure Container Apps) and expose it through Azure API Management to add enterprise-grade features like rate limiting, authentication, and monitoring. After testing the APIM endpoint, we'll expose it as an MCP (Model Context Protocol) server, which allows AI assistants like GitHub Copilot, Claude, or ChatGPT to use your claims processing workflow as a tool. This means AI agents can automatically process insurance claims by simply calling your API, making your workflow accessible to any MCP-compatible AI system.


#### 6.1 Add Your Container App API to APIM

In this step, you'll import your Container App API into Azure API Management. This creates a managed gateway in front of your API, enabling features like subscription keys, rate limiting, caching, and centralized monitoring.

**Steps:**

1. Go to **Azure Portal** → **API Management** → Your APIM instance
2. Navigate to **APIs** in the left menu
3. Click **+ Add API**
4. Scroll down and find the "Create from Azure resource" section and click on **Container App**
5. Browse the name of your container app that we deployed before. Select it and accept the name of the rest of the parameters.
6. Click **Create**

![alt text](images/apim2.png)

Once added, APIM acts as a reverse proxy, forwarding requests to your Container App while applying policies, authentication, and rate limiting.

#### 6.2 Configure APIM Policy for the Upload Operation

The API server now accepts **raw binary uploads** (`application/octet-stream`) in addition to the standard multipart form-data format. This means the APIM inbound policy no longer needs to read or rewrite the request body, which previously caused MCP `tools/list` to time out (body access triggers response buffering that breaks MCP streaming).

> **Why this matters for MCP:** Any APIM policy that accesses `context.Request.Body` or `context.Response.Body` can enable response buffering that interferes with the Server-Sent Events streaming required by MCP servers. The simplified policy below avoids all body access so that `tools/list` and other MCP operations work correctly.

**Steps:**

2. Navigate to **APIs** → Select your Claims Processing API
3. In the **Design** tab, click on the specific **POST /process-claim/upload** operation
4. In the **Inbound processing** section, click **</> Code**

![alt text](images/apim1.png)

5. Replace the entire policy with the following simplified policy (no body transformation required):

```xml
<policies>
    <inbound>
        <base />
        <set-method>POST</set-method>
        <rewrite-uri id="apim-generated-policy" template="/process-claim/upload" />
        <set-header id="apim-generated-policy" name="Ocp-Apim-Subscription-Key" exists-action="delete" />
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>
```

6. Click **Save**

This policy routes the request to the correct backend and strips the internal subscription-key header without touching the request body. The FastAPI server handles both raw binary and multipart form-data transparently.

#### 6.3 Test in APIM Console

1. Download an image file to test (challenge-1/data/statements)
2. Go to the **Test** tab for the `/process-claim/upload` operation
3. Select **Binary** mode (not Raw)

![alt text](images/apim3.png)

4. Upload the file on the **Upload File** button
5. Click **Send**

If you scroll all the way down, you will receive a JSON response with the structured claim data!


## 6.4 Expose API as an MCP Server

Now let's expose the API we have just created as an MCP Server. 

**Steps to Create the MCP Server:**

1. Go to your **APIM Resource**
2. Navigate to **MCPs** section
3. Click on **Create MCP Server** on the top part of your screen
4. Select **Expose an API as an MCP Server**

![alt text](images/apim4.png)

5. Now, let's select the API we have just created. 
6. For the **API Operations**, make sure you select the two POST Operations we have previously created.
7. Fill the rest of the form with something similar as the following image:

![alt text](images/apim5.png)

Perfect! On the next screen, you should be able to see the **MCP Server URL** - copy this URL as you'll need it to connect AI assistants to your claims processing workflow.

### How to Use the MCP Server

The MCP Server URL you just created enables AI assistants to discover and invoke your claims processing API as a tool. Here's how it works:

#### **Connecting AI Assistants to Your MCP Server**

AI assistants that support the Model Context Protocol (MCP) can connect to your server using the URL. When connected, they will:

1. **Discover Available Tools**: The AI reads the MCP server configuration to understand what operations are available (e.g., `process-claim/upload`, `process-claim/base64`)
2. **Understand Tool Capabilities**: The AI learns what each endpoint does, what parameters it accepts, and what format the responses take
3. **Invoke Tools Autonomously**: When a user asks the AI to process a claim, it can automatically call your API with the appropriate data

Now your claims processing workflow is accessible to any AI assistant that supports MCP, enabling natural language interactions with your enterprise-grade insurance processing system!

## Congratulations! 🎉

You've successfully built and deployed a production-ready multi-agent workflow as a REST API on Azure Container Apps with MCP integration! Throughout this challenge, you've orchestrated OCR and JSON structuring agents into a cohesive workflow, containerized the application with Docker, deployed it to Azure Container Apps with auto-scaling and managed identity, exposed it through Azure API Management with enterprise-grade policies, and enabled MCP server integration for AI assistant access. Your claims processing system is now **accessible** via HTTP/HTTPS and AI assistants, **scalable** with automatic replica management, **secure** with managed identity and APIM authentication, **observable** with Application Insights monitoring, and **AI-native** with MCP protocol support.

From Challenge 1 to Challenge 4, you've built a complete AI-powered insurance claims processing system that processes insurance claims automatically through AI agents, scales elastically based on demand, integrates with both traditional applications (web apps, business systems, insurance platforms) and modern AI assistants (GitHub Copilot, Claude Desktop, ChatGPT), and maintains enterprise-grade security and observability. This is the foundation for building intelligent, autonomous systems that bridge traditional enterprise workflows with cutting-edge AI capabilities!

Great work completing this challenge! 🚀

This is the foundation for building intelligent, autonomous systems that bridge traditional enterprise workflows with cutting-edge AI capabilities!
