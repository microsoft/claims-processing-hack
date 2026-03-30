# Challenge 5: Claims Processing UI

**Expected Duration:** 30 minutes

## Introduction

Welcome to Challenge 5! In this challenge, you'll build a user-friendly web interface using **Streamlit** to consume the Claims Processing REST API you deployed in Challenge 4. This UI will allow users to upload insurance claim images and view the structured results extracted by the multi-agent workflow—completing the end-to-end claims processing solution.

### MCP vs REST API: When to Use Each

In Challenge 4, you deployed your claims processing workflow with both **MCP (Model Context Protocol)** and **REST API** endpoints. Understanding when to use each is important:

| Approach       | Best For                                                                      | Examples                                                          |
| -------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **MCP Server** | AI assistants and agents that need to discover and invoke tools dynamically   | GitHub Copilot, Claude Desktop, ChatGPT plugins, AI coding agents |
| **REST API**   | Traditional applications, web UIs, mobile apps, and programmatic integrations | Streamlit apps, React frontends, mobile apps, backend services    |

**MCP** is designed for AI-to-tool communication—it allows AI assistants to discover available tools, understand their parameters, and invoke them through a standardized protocol. **REST APIs** are the standard for application-to-application communication, providing predictable endpoints that any HTTP client can consume.

For this challenge, we use the **REST API** since we're building a traditional web interface, not an AI assistant.

## What are we building?

In this challenge, you will create:

- **Streamlit Web App**: A simple, interactive UI for uploading and processing claim images
- **REST API Integration**: Connect to the Challenge 4 REST API to process claims
- **Results Display**: Parse and display structured claim data (vehicle info, damage assessment, incident details)

## Architecture

```
┌──────────────────────────────────┐
│     Streamlit UI (this app)      │
│     http://localhost:8501        │
└──────────────┬───────────────────┘
               │
               │ HTTP REST API
               │
┌──────────────▼───────────────────┐
│     Claims Processing API        │
│     Azure Container Apps         │
│  /health, /process-claim/upload  │
└──────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd challenge-5
pip install -r requirements.txt
```

### 2. Get your API URL from Challenge 4

Use the **Container Apps URL** from your Challenge 4 deployment:

```bash
# Your API URL should look like:
# https://<your-app-name>.<environment>.<region>.azurecontainerapps.io
```

You can find this URL:

1. In the Azure Portal → **Container Apps** → Your app → **Overview** → **Application Url**
2. Or from the deployment output in Challenge 4

### 3. Start the Streamlit UI

```bash
cd challenge-5
API_URL=https://<your-container-app-url> streamlit run app.py
```

Or configure the API URL in the sidebar after launching:

```bash
streamlit run app.py
```

### 4. Open in Browser

Navigate to http://localhost:8501

## Usage

1. **Configure API URL**: In the sidebar, enter your Container Apps API URL
2. **Check Health**: Click "Check Health" to verify connectivity
3. **Upload Image**: Use the file uploader to select a claim image
4. **Process**: Click "Process Claim" to send the image to the API
5. **View Results**: See the structured claim data displayed in a user-friendly format

## UI Features

### 📤 Upload Claim

- File uploader for claim images (JPG, JPEG, PNG)
- Preview of uploaded image
- One-click claim processing
- Results display with structured data

### 📋 Results Display

- Vehicle information (make, model, color, year)
- Damage assessment (severity, estimated cost, affected areas)
- Incident details (date, location, description)
- Raw JSON expandable view

## Configuration

### Environment Variables

| Variable  | Description               | Default                 |
| --------- | ------------------------- | ----------------------- |
| `API_URL` | Claims Processing API URL | `http://localhost:8000` |

### Sidebar Settings

- **API URL**: Can be changed dynamically in the sidebar
- **Health Check**: Test API connectivity

## Development

### Extending the UI

To add new features:

1. Add new tabs in the `tabs` section of `main()`
2. Create helper functions for API calls
3. Use Streamlit components for display

## Conclusion

Congratulations! 🎉 You've successfully built a complete end-to-end claims processing solution:

1. **Challenge 0-3**: Built the AI agents for document processing, OCR, and data extraction
2. **Challenge 4**: Deployed the multi-agent workflow as a REST API on Azure Container Apps
3. **Challenge 5**: Created a user-friendly web interface to interact with the API

Your Streamlit UI now allows users to easily upload claim images and receive structured data extracted by your AI-powered backend.

### Next Steps

Ready to take it further? Deploy this Streamlit UI to **Azure Container Apps** for a fully cloud-hosted solution using the provided script. It reads your ACR, Container Apps environment, and resource group from the `.env` file (generated by Challenge 0's `get-keys.sh`), and looks up the API URL from the running `claims-processing-api` container app:

```bash
cd challenge-5
./deploy-ui-to-aca.sh
```

Once complete, the script prints your live UI URL.

## Related

- [Challenge 4: API Server](../challenge-4/README.md)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Deploy Streamlit to Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
