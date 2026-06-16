# Challenge 0 - Environment Creation and Resources Deployment

**Expected Duration:** 30 minutes

Welcome to your very first challenge! Your goal in this challenge is to create the services and environment necessary to conduct this hackathon. You will deploy the required resources in Azure, create your development environment and all the assets necessary for the subsequent challenges. By completing this challenge, you will set up the foundation for the rest of the hackathon. 

If something is not working correctly, please do let your coach know!


## 1.1 Fork the Repository

Before you start, please fork this repository to your GitHub account by clicking the `Fork` button in the upper right corner of the repository's main screen (or follow the [documentation](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo#forking-a-repository)). This will allow you to make changes to the repository and save your progress.


## 1.2 Development Environment

GitHub Codespaces is a cloud-based development environment that allows you to code from anywhere. It provides a fully configured environment that can be launched directly from any GitHub repository, saving you from lengthy setup times. You can access Codespaces from your browser, Visual Studio Code, or the GitHub CLI, making it easy to work from virtually any device.

To open GitHub Codespaces, click on the button below:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/)

Please select your forked repository from the dropdown and, if necessary, adjust other settings of GitHub Codespace.


> [!NOTE]
> If GitHub Codespaces is not enabled in your organization, you can enable it by following the instructions [here](https://docs.github.com/en/codespaces/managing-codespaces-for-your-organization/enabling-or-disabling-github-codespaces-for-your-organization), or, if you cannot change your GitHub organization's settings, create a free personal GitHub account [here](https://github.com/signup?ref_cta=Sign+up&ref_loc=header+logged+out&ref_page=%2F&source=header-home). The Github Free Plan includes 120 core hours per month, equivalent to 60 hours on a 2-core machine, along with 15 GB of storage.


## 1.3 Resource Deployment Guide
The first step on this hackathon will be to create the resources we will use throughout the day. You can deploy using either the one-click button or manual method below.

Before anything else, let's log in into the CLI with our account. Please paste the code underneath and follow the necessary instructions.

```bash
az login --use-device-code
```

## 1.3.1 Resources Deployment

Now, time to deploy our resources to Azure!

- When clicking on Deploy to Azure, under Resource group, select the "Create new" option and give it a name with your initials, for example "rg-claims-processing-\<initials\>"

- Select Region "Sweden Central" and Location "swedencentral"

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fmicrosoft%2Fclaims-processing-hack%2Fmain%2Fchallenge-0%2Finfra%2Fazuredeploy.json)

**NOTE:** Some parts of your deployment may fail if the resource provider `Microsoft.AlertsManagement` is not registered in your subscription. Follow the [documentation](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-providers-and-types#register-resource-provider-1) to register it and the re-run the deployment.

Resource deployment can take up to 10 minutes, afterwards you'll be able to find all the Azure resources you need in your resource group.

## 1.4 Verify the creation of your resources

Go to your [`Azure Portal`](https://portal.azure.com/) and find your `Resource Group`that should by now contain 10 Azure resources.


## 1.5 Let's retrieve the necessary keys
After deploying resources, configure environment variables in the `.env` file. Ensure you're logged into Azure CLI, then run the get-keys script to automatically populate the required values.

**Then run the get-keys script with your resource group name:**
```bash
cd challenge-0 && ./get-keys.sh --resource-group YOUR_RESOURCE_GROUP_NAME
```

Replace `YOUR_RESOURCE_GROUP_NAME` with the actual name of the resource group created.

This script will:
1. Connect to Azure and fetch the necessary keys
2. **Assign Azure AI Developer and Cognitive Services User roles** to your user account (required for AI Foundry agent management)
3. Populate the `.env` file with the required values in the root directory of the repository

## 1.6 Verify `.env` setup

Review the generated `.env` file to ensure all values are correct. The script creates this file from `.env.sample` with populated Azure resource values. If the file isn't created automatically, copy `.env.sample` to `.env` and populate values manually from the Azure Portal.


> [!CAUTION]
>For convenience we will use key-based authentication and public network access to resources in the hack. In real world implementations you should consider stronger authentication mechanisms and additional network security.


## Conclusion
By reaching this section you should have every resource and installed the requirements necessary to conduct the hackathon. In the next challenges, you will use these resources to start strongly your Azure AI Agents journey.

Now the real fun begins!