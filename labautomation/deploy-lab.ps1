param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('subscription','resourcegroup','resourcegroup-with-subscriptionowner')]
    [string]$DeploymentType,

    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId,

    [string]$ResourceGroupName = "",

    [string[]]$PreferredLocation = @(),

    [string[]]$AllowedEntraUserIds = @()
)

# Get the script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Resolve effective location
$effectiveLocation = if ($PreferredLocation.Count -gt 0) { $PreferredLocation[0] } else { "westeurope" }

Write-Host "🚀 Claims Processing Hackathon - Lab Deployment" -ForegroundColor Cyan
Write-Host "DeploymentType: $DeploymentType" -ForegroundColor Yellow
Write-Host "Subscription ID: $SubscriptionId" -ForegroundColor Yellow
Write-Host "Location: $effectiveLocation" -ForegroundColor Yellow
Write-Host "ResourceGroupName: $ResourceGroupName" -ForegroundColor Yellow
Write-Host ""

# Ensure we're in the correct subscription context
$currentContext = Get-AzContext
if ($currentContext.Subscription.Id -ne $SubscriptionId) {
    Write-Host "⚠️ Switching to subscription: $SubscriptionId" -ForegroundColor Yellow
    Set-AzContext -SubscriptionId $SubscriptionId | Out-Null
}

# Determine effective resource group name
$effectiveResourceGroup = $ResourceGroupName

# For 'subscription' mode, create resource group with deterministic name
if ($DeploymentType -eq 'subscription') {
    $stableHash = Get-MhhStableHash $AllowedEntraUserIds -Length 24
    $effectiveResourceGroup = "lab-$stableHash"
    
    Write-Host "📦 Creating resource group (subscription mode): $effectiveResourceGroup" -ForegroundColor Yellow
    New-AzResourceGroup -Name $effectiveResourceGroup -Location $effectiveLocation -Force | Out-Null
}

# Template file path
$templateFile = Join-Path $scriptPath "..\challenge-1\infra\azuredeploy.json"

if (-not (Test-Path $templateFile)) {
    Write-Host "❌ Error: Template file not found at $templateFile" -ForegroundColor Red
    exit 1
}

# Deploy resources
Write-Host "📋 Deploying infrastructure resources..." -ForegroundColor Yellow
try {
    $deployment = New-AzResourceGroupDeployment `
        -ResourceGroupName $effectiveResourceGroup `
        -TemplateFile $templateFile `
        -location $effectiveLocation `
        -Verbose -ErrorAction Stop
    
    Write-Host "✅ Deployment succeeded!" -ForegroundColor Green
} catch {
    Write-Host "❌ Deployment failed: $_" -ForegroundColor Red
    exit 1
}

# Extract important outputs
$outputs = @{
    ResourceGroupName = $effectiveResourceGroup
    Location = $effectiveLocation
    DeploymentType = $DeploymentType
}

# Get deployed resource names from template outputs
Write-Host ""
Write-Host "📊 Deployed Resources:" -ForegroundColor Cyan

# Extract resources from deployment
$resources = Get-AzResource -ResourceGroupName $effectiveResourceGroup

foreach ($resource in $resources) {
    Write-Host "  ✓ $($resource.ResourceType): $($resource.Name)" -ForegroundColor Green
}

# Return credentials/info to the platform
Write-Host ""
Write-Host "📤 Returning lab credentials to platform..." -ForegroundColor Yellow

@{
    HackboxCredential = @{
        name = "ResourceGroupName"
        value = $effectiveResourceGroup
        note = "Azure Resource Group containing all lab resources"
    }
}

@{
    HackboxCredential = @{
        name = "DeploymentLocation"
        value = $effectiveLocation
        note = "Azure region where resources are deployed"
    }
}

# Return resource names for easy access
$storageAccounts = $resources | Where-Object { $_.ResourceType -eq 'Microsoft.Storage/storageAccounts' }
if ($storageAccounts) {
    @{
        HackboxCredential = @{
            name = "StorageAccountName"
            value = $storageAccounts[0].Name
            note = "Storage Account for data and artifacts"
        }
    }
}

$containerRegistry = $resources | Where-Object { $_.ResourceType -eq 'Microsoft.ContainerRegistry/registries' }
if ($containerRegistry) {
    @{
        HackboxCredential = @{
            name = "ContainerRegistryName"
            value = $containerRegistry[0].Name
            note = "Azure Container Registry for Docker images"
        }
    }
}

$cosmosDb = $resources | Where-Object { $_.ResourceType -eq 'Microsoft.DocumentDB/databaseAccounts' }
if ($cosmosDb) {
    @{
        HackboxCredential = @{
            name = "CosmosDbAccountName"
            value = $cosmosDb[0].Name
            note = "Cosmos DB account for claims data"
        }
    }
}

$aiFoundry = $resources | Where-Object { $_.ResourceType -eq 'Microsoft.CognitiveServices/accounts' -and $_.Name -like '*aifoundry*' }
if ($aiFoundry) {
    @{
        HackboxCredential = @{
            name = "AIFoundryName"
            value = $aiFoundry[0].Name
            note = "AI Foundry hub for agents and models"
        }
    }
}

Write-Host "✅ Lab deployment complete!" -ForegroundColor Green
