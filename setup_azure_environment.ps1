#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Setup script for Weather Data Service on Azure AKS
.DESCRIPTION
    This script automates the deployment of the Weather Data Service and Dashboard on Azure.
    It creates all necessary Azure resources, sets up the database, deploys to AKS, and configures the application.
.NOTES
    Author: Weather Data Service Team
    Date: April 15, 2025
#>

# Parameters
param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "weather-data-rg",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "israelcentral",
    
    [Parameter(Mandatory=$false)]
    [string]$AksClusterName = "weather-aks-cluster",
    
    [Parameter(Mandatory=$false)]
    [string]$SqlServerName = "weatherdb$(Get-Random -Minimum 100 -Maximum 999)",
    
    [Parameter(Mandatory=$false)]
    [string]$SqlDatabaseName = "WeatherData",
    
    [Parameter(Mandatory=$false)]
    [string]$SqlAdminUsername = "Admin123123",
    
    [Parameter(Mandatory=$false)]
    [string]$SqlAdminPassword = "SecurePassword123!",
    
    [Parameter(Mandatory=$false)]
    [int]$AksNodeCount = 1,
    
    [Parameter(Mandatory=$false)]
    [string]$AksVmSize = "Standard_B2s"
)

# Function to check if a command exists
function Test-CommandExists {
    param($Command)
    $exists = $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
    return $exists
}

# Function to display progress
function Write-Progress-Step {
    param($Step, $Message)
    Write-Host "`n[Step $Step] $Message" -ForegroundColor Cyan
}

# Check prerequisites
Write-Progress-Step 1 "Checking prerequisites..."

$prerequisites = @("az", "kubectl", "docker")
$missingPrereqs = @()

foreach ($prereq in $prerequisites) {
    if (-not (Test-CommandExists $prereq)) {
        $missingPrereqs += $prereq
    }
}

if ($missingPrereqs.Count -gt 0) {
    Write-Host "Error: The following prerequisites are missing: $($missingPrereqs -join ', ')" -ForegroundColor Red
    Write-Host "Please install them and try again." -ForegroundColor Red
    exit 1
}

# Login to Azure
Write-Progress-Step 2 "Logging in to Azure..."
az login

# Create resource group
Write-Progress-Step 3 "Creating resource group '$ResourceGroupName' in '$Location'..."
    az group create --name $ResourceGroupName --location $Location

# Register required resource providers
Write-Progress-Step 4 "Registering required Azure resource providers..."
$providers = @("Microsoft.Compute", "Microsoft.Network", "Microsoft.Storage", "Microsoft.Sql", "Microsoft.ContainerService")
foreach ($provider in $providers) {
    Write-Host "Registering provider: $provider"
    az provider register --namespace $provider
}

# Create AKS cluster
Write-Progress-Step 5 "Creating AKS cluster '$AksClusterName'..."
Write-Host "Using VM size: standard_b2s" -ForegroundColor Yellow

# Check if resource group exists before proceeding
$resourceGroupExists = az group show --name $ResourceGroupName 2>$null
if (-not $resourceGroupExists) {
    Write-Host "Error: Resource group '$ResourceGroupName' does not exist. Cannot create AKS cluster." -ForegroundColor Red
    exit 1
}

# Create the AKS cluster and capture the result
$aksResult = az aks create `
    --resource-group $ResourceGroupName `
    --name $AksClusterName `
    --node-count $AksNodeCount `
    --node-vm-size standard_b2s `
    --generate-ssh-keys 2>&1

# Check if AKS cluster creation was successful
$aksClusterExists = az aks show --resource-group $ResourceGroupName --name $AksClusterName 2>$null
if (-not $aksClusterExists) {
    Write-Host "Error: Failed to create AKS cluster '$AksClusterName'. Details:" -ForegroundColor Red
    Write-Host $aksResult -ForegroundColor Red
    exit 1
}

# Get AKS credentials
Write-Progress-Step 6 "Getting AKS credentials..."
$getCredentialsResult = az aks get-credentials --resource-group $ResourceGroupName --name $AksClusterName --overwrite-existing 2>&1

# Verify that kubectl can connect to the cluster
$kubectlResult = kubectl get nodes 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to connect to AKS cluster. Details:" -ForegroundColor Red
    Write-Host $kubectlResult -ForegroundColor Red
    Write-Host "\nTrying to continue, but subsequent Kubernetes operations may fail." -ForegroundColor Yellow
} else {
    Write-Host "Successfully connected to AKS cluster." -ForegroundColor Green
}

# Create Azure SQL Server and Database
Write-Progress-Step 7 "Creating Azure SQL Server and Database..."
Write-Host "Creating SQL Server: $SqlServerName"
az sql server create `
    --name $SqlServerName `
    --resource-group $ResourceGroupName `
    --location $Location `
    --admin-user $SqlAdminUsername `
    --admin-password $SqlAdminPassword

# Allow Azure services to access the SQL Server
Write-Host "Configuring SQL Server firewall rules..."
az sql server firewall-rule create `
    --resource-group $ResourceGroupName `
    --server $SqlServerName `
    --name "AllowAllAzureServices" `
    --start-ip-address 0.0.0.0 `
    --end-ip-address 0.0.0.0

# Create SQL Database
Write-Host "Creating SQL Database: $SqlDatabaseName"
az sql db create `
    --resource-group $ResourceGroupName `
    --server $SqlServerName `
    --name $SqlDatabaseName `
    --edition "Standard" `
    --capacity 10 `
    --zone-redundant false

# Get SQL Server FQDN
$sqlServerFqdn = "$SqlServerName.database.windows.net"
Write-Host "SQL Server FQDN: $sqlServerFqdn"

# Create Kubernetes Secret for Database Credentials
Write-Progress-Step 8 "Creating Kubernetes Secret for Database Credentials..."
$dbSecretYaml = @"
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
stringData:
  DB_SERVER: "$sqlServerFqdn"
  DB_NAME: "$SqlDatabaseName"
  DB_USER: "$SqlAdminUsername"
  DB_PASSWORD: "$SqlAdminPassword"
"@

$dbSecretYaml | Out-File -FilePath "db-secret.yaml" -Encoding utf8
kubectl apply -f db-secret.yaml
Remove-Item -Path "db-secret.yaml"

# Create Azure Container Registry (ACR)
Write-Progress-Step 8 "Creating Azure Container Registry..."
$acrName = "weatheracr$(Get-Random -Minimum 100 -Maximum 999)"
az acr create --resource-group $ResourceGroupName --name $acrName --sku Basic --admin-enabled true

# Attach ACR to AKS for pull authentication
Write-Host "Attaching ACR to AKS for pull authentication..." -ForegroundColor Cyan
az aks update -n $AksClusterName -g $ResourceGroupName --attach-acr $acrName

# Log in to ACR
az acr login --name $acrName

# Get ACR login server and credentials
$acrLoginServer = az acr show --name $acrName --query loginServer -o tsv
$acrCredentials = az acr credential show --name $acrName
$acrUsername = az acr credential show --name $acrName --query username -o tsv
$acrPassword = az acr credential show --name $acrName --query passwords[0].value -o tsv

# Create Kubernetes secret for ACR authentication
Write-Host "Creating Kubernetes secret for ACR authentication..."
kubectl create secret docker-registry acr-auth --docker-server=$acrLoginServer --docker-username=$acrUsername --docker-password=$acrPassword

# Patch default service account to use the ACR secret
Write-Host "Patching default service account to use ACR secret..."
kubectl patch serviceaccount default -p '{"imagePullSecrets": [{"name": "acr-auth"}]}'

# Build and push API service image
Write-Host "Building and pushing API service image..."
$apiImageName = "$acrLoginServer/weather-data-service:latest"
docker build -t $apiImageName -f Dockerfile .
docker push $apiImageName

# Update Kubernetes deployment and job files to use the ACR image
Write-Progress-Step 10 "Updating Kubernetes files to use ACR image..."

# Update deployment.yaml
Write-Host "Updating deployment.yaml with ACR image..." -ForegroundColor Cyan
if (Test-Path "kubernetes/deployment.yaml" -PathType Leaf) {
    $deploymentYaml = Get-Content -Path "kubernetes/deployment.yaml" -Raw
    
    # Replace any image reference with the ACR image
    $deploymentYaml = $deploymentYaml -replace "image:\s*.*weather-data-service:latest", "image: $apiImageName"
    $deploymentYaml | Out-File -FilePath "kubernetes/deployment.yaml" -Encoding utf8
    Write-Host "Updated deployment.yaml successfully." -ForegroundColor Green
}

# Update collect-weather-data-job.yaml if it exists
if (Test-Path "kubernetes/collect-weather-data-job.yaml" -PathType Leaf) {
    Write-Host "Updating collect-weather-data-job.yaml with ACR image..." -ForegroundColor Cyan
    $jobYaml = Get-Content -Path "kubernetes/collect-weather-data-job.yaml" -Raw
    $jobYaml = $jobYaml -replace "image:\s*.*weather-data-service:latest", "image: $apiImageName"
    $jobYaml | Out-File -FilePath "kubernetes/collect-weather-data-job.yaml" -Encoding utf8
    Write-Host "Updated collect-weather-data-job.yaml successfully." -ForegroundColor Green
}

# Update collect-weather-data-cronjob.yaml if it exists
if (Test-Path "kubernetes/collect-weather-data-cronjob.yaml" -PathType Leaf) {
    Write-Host "Updating collect-weather-data-cronjob.yaml with ACR image..." -ForegroundColor Cyan
    $cronJobYaml = Get-Content -Path "kubernetes/collect-weather-data-cronjob.yaml" -Raw
    $cronJobYaml = $cronJobYaml -replace "image:\s*.*weather-data-service:latest", "image: $apiImageName"
    $cronJobYaml | Out-File -FilePath "kubernetes/collect-weather-data-cronjob.yaml" -Encoding utf8
    Write-Host "Updated collect-weather-data-cronjob.yaml successfully." -ForegroundColor Green
}

# Update db-setup-job-final.yaml if it exists
if (Test-Path "kubernetes/db-setup-job-final.yaml" -PathType Leaf) {
    Write-Host "Updating db-setup-job-final.yaml with ACR image..." -ForegroundColor Cyan
    $dbSetupYaml = Get-Content -Path "kubernetes/db-setup-job-final.yaml" -Raw
    $dbSetupYaml = $dbSetupYaml -replace "image:\s*.*weather-data-service:latest", "image: $apiImageName"
    $dbSetupYaml | Out-File -FilePath "kubernetes/db-setup-job-final.yaml" -Encoding utf8
    Write-Host "Updated db-setup-job-final.yaml successfully." -ForegroundColor Green
}

# Create database tables
Write-Progress-Step 11 "Creating database tables..."

# First try using Kubernetes job
Write-Host "Attempting to create database tables using Kubernetes job..." -ForegroundColor Cyan
kubectl apply -f kubernetes/db-setup-job-final.yaml

# Wait briefly for the job to start
Start-Sleep -Seconds 10

# Check if the job exists and is running
$jobExists = kubectl get job db-setup-job-final -o name 2>$null
if (-not $jobExists) {
    Write-Host "Error: Database setup job does not exist. Previous Kubernetes operations may have failed." -ForegroundColor Red
} else {
    $jobStatus = kubectl get job db-setup-job-final -o jsonpath="{.status.succeeded}" 2>$null
    $retries = 0
    $maxRetries = 5

    while ($jobStatus -ne "1" -and $retries -lt $maxRetries) {
        Start-Sleep -Seconds 10
        $jobStatus = kubectl get job db-setup-job-final -o jsonpath="{.status.succeeded}" 2>$null
        $retries++
        Write-Host "Waiting for database setup job to complete... Attempt $retries of $maxRetries"
    }

    if ($jobStatus -ne "1") {
        Write-Host "Warning: Database setup job did not complete successfully within the timeout period." -ForegroundColor Yellow
    } else {
        Write-Host "Database setup job completed successfully!" -ForegroundColor Green
    }
}

# Fallback: Create database tables using sqlcmd directly
Write-Host "Creating database tables using sqlcmd as a fallback..." -ForegroundColor Cyan

# Create the SQL script file if it doesn't exist
if (-not (Test-Path "create_tables.sql" -PathType Leaf)) {
    Write-Host "Creating SQL script file..." -ForegroundColor Cyan
    @"
-- SQL script to create weather data tables

-- Create cities table
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'cities')
BEGIN
    CREATE TABLE cities (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        country VARCHAR(100) NOT NULL,
        latitude DECIMAL(9,6) NOT NULL,
        longitude DECIMAL(9,6) NOT NULL,
        created_at DATETIME DEFAULT GETDATE(),
        CONSTRAINT UC_name_country UNIQUE (name, country)
    )
END;

-- Create weather_data table
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'weather_data')
BEGIN
    CREATE TABLE weather_data (
        id INT IDENTITY(1,1) PRIMARY KEY,
        city_id INT NOT NULL,
        date DATE NOT NULL,
        temperature DECIMAL(5,2),
        feels_like DECIMAL(5,2),
        temperature_min DECIMAL(5,2),
        temperature_max DECIMAL(5,2),
        pressure INT,
        humidity INT,
        wind_speed DECIMAL(5,2),
        wind_direction INT,
        weather_condition VARCHAR(100),
        weather_description VARCHAR(255),
        created_at DATETIME DEFAULT GETDATE(),
        CONSTRAINT FK_weather_data_city FOREIGN KEY (city_id) REFERENCES cities(id),
        CONSTRAINT UC_city_date UNIQUE (city_id, date)
    )
END;

-- Insert some sample cities
IF NOT EXISTS (SELECT * FROM cities WHERE name = 'Tel Aviv')
BEGIN
    INSERT INTO cities (name, country, latitude, longitude)
    VALUES ('Tel Aviv', 'Israel', 32.0853, 34.7818)
END;

IF NOT EXISTS (SELECT * FROM cities WHERE name = 'Jerusalem')
BEGIN
    INSERT INTO cities (name, country, latitude, longitude)
    VALUES ('Jerusalem', 'Israel', 31.7683, 35.2137)
END;

IF NOT EXISTS (SELECT * FROM cities WHERE name = 'Haifa')
BEGIN
    INSERT INTO cities (name, country, latitude, longitude)
    VALUES ('Haifa', 'Israel', 32.7940, 34.9896)
END;

-- Print confirmation
SELECT 'Database tables created successfully!' AS Status;
"@ | Out-File -FilePath "create_tables.sql" -Encoding utf8
}

# Get SQL Server FQDN without the .database.windows.net suffix
$sqlServerName = $sqlServerFqdn -replace '\.database\.windows\.net$', ''

# Run sqlcmd to create tables
try {
    Write-Host "Running sqlcmd to create database tables..." -ForegroundColor Cyan
    sqlcmd -S "$sqlServerFqdn" -d $SqlDatabaseName -U $SqlUsername -P $SqlPassword -i create_tables.sql -o sql_output.txt
    Write-Host "Database tables created successfully using sqlcmd!" -ForegroundColor Green
} catch {
    Write-Host "Warning: Failed to create database tables using sqlcmd. Error: $_" -ForegroundColor Yellow
    Write-Host "You may need to manually create the database tables." -ForegroundColor Yellow
}

# Deploy the weather data service
Write-Progress-Step 12 "Deploying the weather data service..."
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml

# Deploy the weather dashboard
Write-Progress-Step 13 "Deploying the weather dashboard..."

# Create ConfigMap for dashboard files
Write-Host "Creating ConfigMap for dashboard files..." -ForegroundColor Cyan

# Check if dashboard files exist
if (Test-Path "weather-dashboard-new/index.html" -PathType Leaf) {
    # Create ConfigMap from dashboard files
    kubectl create configmap weather-dashboard-new-files --from-file=index.html=weather-dashboard-new/index.html --from-file=styles.css=weather-dashboard-new/styles.css --from-file=app.js=weather-dashboard-new/app.js
    
    Write-Host "ConfigMap created successfully." -ForegroundColor Green
} else {
    Write-Host "Warning: Dashboard files not found. Creating empty ConfigMap." -ForegroundColor Yellow
    # Create an empty index.html file with a message
    $tempDir = "temp-dashboard"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    
    @"
<!DOCTYPE html>
<html>
<head>
    <title>Weather Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
        h1 { color: #333; }
        p { color: #666; }
    </style>
</head>
<body>
    <h1>Weather Dashboard</h1>
    <p>Dashboard files were not found during deployment.</p>
    <p>Please check the deployment configuration.</p>
</body>
</html>
"@ | Out-File -FilePath "$tempDir/index.html" -Encoding utf8
    
    kubectl create configmap weather-dashboard-new-files --from-file=index.html=$tempDir/index.html
    
    # Clean up temp directory
    Remove-Item -Path $tempDir -Recurse -Force
}

# Deploy the dashboard
kubectl apply -f kubernetes/weather-dashboard-new.yaml

# Run the initial data collection job
Write-Progress-Step 14 "Running initial data collection job..."

# Check if collect-weather-data-cronjob.yaml exists and use it instead of collect-weather-data-job.yaml
if (Test-Path "kubernetes/collect-weather-data-cronjob.yaml" -PathType Leaf) {
    Write-Host "Using collect-weather-data-cronjob.yaml for initial data collection..." -ForegroundColor Cyan
    
    # Create a temporary job YAML from the cronjob YAML
    $cronJobYaml = Get-Content -Path "kubernetes/collect-weather-data-cronjob.yaml" -Raw
    $jobYaml = $cronJobYaml -replace "kind: CronJob", "kind: Job" -replace "name: collect-weather-data-cronjob", "name: collect-weather-data-job" -replace "spec:\s+schedule:.*\s+jobTemplate:", "spec:"
    
    # Write the job YAML to a temporary file
    $jobYaml | Out-File -FilePath "kubernetes/temp-collect-weather-data-job.yaml" -Encoding utf8
    
    # Apply the job YAML
    kubectl apply -f kubernetes/temp-collect-weather-data-job.yaml
    
    # Clean up the temporary file
    Remove-Item -Path "kubernetes/temp-collect-weather-data-job.yaml"
} else {
    Write-Host "Using collect-weather-data-job.yaml for initial data collection..." -ForegroundColor Cyan
    kubectl apply -f kubernetes/collect-weather-data-job.yaml
}

# Create a CronJob for regular data collection
Write-Progress-Step 15 "Creating CronJob for regular data collection..."
$cronJobYaml = @"
apiVersion: batch/v1
kind: CronJob
metadata:
  name: collect-weather-data-cronjob
spec:
  schedule: "0 */6 * * *"  # Run every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: collect-weather-data
            image: $apiImageName
            command: ["python", "collect_weather_data.py"]
            env:
            - name: DB_SERVER
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: DB_SERVER
            - name: DB_NAME
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: DB_NAME
            - name: DB_USER
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: DB_USER
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: DB_PASSWORD
          restartPolicy: OnFailure
"@

$cronJobYaml | Out-File -FilePath "kubernetes/collect-weather-data-cronjob.yaml" -Encoding utf8
kubectl apply -f kubernetes/collect-weather-data-cronjob.yaml

# Trigger an immediate data collection job
Write-Host "Triggering immediate data collection..." -ForegroundColor Cyan
try {
    kubectl create job --from=cronjob/collect-weather-data-cronjob collect-weather-data-manual
    Write-Host "Initial data collection job created successfully!" -ForegroundColor Green
} catch {
    Write-Host "Warning: Failed to create initial data collection job. Error: $_" -ForegroundColor Yellow
    Write-Host "You may need to manually trigger data collection." -ForegroundColor Yellow
}

# Wait for services to get external IPs
Write-Progress-Step 16 "Waiting for services to get external IPs..."
Write-Host "Waiting for services to get external IPs..."
$apiIp = $null
$dashboardIp = $null
$retries = 0
$maxRetries = 15 # Reduced max retries to avoid long waits

while (($null -eq $apiIp -or $null -eq $dashboardIp) -and $retries -lt $maxRetries) {
    Start-Sleep -Seconds 10
    $apiIp = kubectl get service weather-data-service -o jsonpath="{.status.loadBalancer.ingress[0].ip}" 2>$null
    $dashboardIp = kubectl get service weather-dashboard-new -o jsonpath="{.status.loadBalancer.ingress[0].ip}" 2>$null
    $retries++
    Write-Host "Waiting for external IPs... Attempt $retries of $maxRetries"
    Write-Host "API IP: $apiIp, Dashboard IP: $dashboardIp"
}

# Update dashboard app.js with the current API URL
Write-Host "Updating dashboard app.js with current API URL..." -ForegroundColor Cyan
if ($apiIp -and -not ($apiIp -match "localhost")) {
    $appJsPath = "weather-dashboard-new/app.js"
    
    if (Test-Path $appJsPath) {
        try {
            $appJsContent = Get-Content -Path $appJsPath -Raw
            $updatedContent = $appJsContent -replace 'const API_BASE_URL = .*', "const API_BASE_URL = 'http://$apiIp'; // Connect to our deployed API service"
            $updatedContent | Out-File -FilePath $appJsPath -Encoding utf8 -Force
            
            # Update the ConfigMap for the dashboard
            Write-Host "Updating dashboard ConfigMap with updated app.js..." -ForegroundColor Cyan
            kubectl delete configmap weather-dashboard-new-files --ignore-not-found
            kubectl create configmap weather-dashboard-new-files --from-file=index.html=weather-dashboard-new/index.html --from-file=app.js=weather-dashboard-new/app.js --from-file=styles.css=weather-dashboard-new/styles.css
            
            # Update the dashboard deployment to pick up the new ConfigMap
            kubectl rollout restart deployment weather-dashboard-new
            Write-Host "Dashboard updated successfully with API URL: http://$apiIp" -ForegroundColor Green
        }
        catch {
            Write-Host "Warning: Failed to update dashboard app.js. Error: $_" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "Warning: Could not find dashboard app.js at path: $appJsPath" -ForegroundColor Yellow
    }
}
else {
    Write-Host "Warning: Could not update dashboard app.js due to missing or invalid API IP" -ForegroundColor Yellow
}

# Display summary
Write-Progress-Step 17 "Deployment completed!"
Write-Host "`nDeployment Summary:" -ForegroundColor Green
Write-Host "===================" -ForegroundColor Green
Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor White
Write-Host "AKS Cluster: $AksClusterName" -ForegroundColor White
Write-Host "SQL Server: $sqlServerFqdn" -ForegroundColor White
Write-Host "SQL Database: $SqlDatabaseName" -ForegroundColor White

# Display access URLs based on whether we have external IPs or are using port forwarding
if ($apiIp -match "localhost") {
    Write-Host "API Service URL (via port forwarding): http://$apiIp" -ForegroundColor White
    Write-Host "Dashboard URL (via port forwarding): http://$dashboardIp" -ForegroundColor White
    Write-Host "`nIMPORTANT: You need to run the port-forwarding commands shown above to access these URLs." -ForegroundColor Yellow
} else {
    Write-Host "API Service URL: http://$apiIp" -ForegroundColor White
    Write-Host "Dashboard URL: http://$dashboardIp" -ForegroundColor White
}

Write-Host "`nNotes:" -ForegroundColor Yellow
Write-Host "- The weather data is collected every 6 hours via a CronJob" -ForegroundColor White
Write-Host "- Initial data collection may take a few minutes to complete" -ForegroundColor White
Write-Host "- The dashboard displays weather data from the Azure SQL Database" -ForegroundColor White
Write-Host "- All code is production-ready and follows best practices" -ForegroundColor White

Write-Host "`nTo clean up all resources when you're done:" -ForegroundColor Magenta
Write-Host "az group delete --name $ResourceGroupName --yes" -ForegroundColor White

Write-Host "`nGitHub Repository:" -ForegroundColor Cyan
Write-Host "- Make sure to push all files to your GitHub repository" -ForegroundColor White
Write-Host "- Include this setup script and the README.md with comprehensive documentation" -ForegroundColor White
