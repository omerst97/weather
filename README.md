# Weather Dashboard on Azure Kubernetes Service

A production-ready weather dashboard that automatically collects, stores, and visualizes weather data for cities around the world. This project provides a fully automated deployment process to Azure Kubernetes Service (AKS) with a single command.

![Weather Dashboard](https://via.placeholder.com/800x400?text=Weather+Dashboard)

## Quick Start

To deploy the entire solution to Azure, simply run:

```powershell
./setup_azure_environment.ps1
```
***This script automates azure login, you just need to choose subscription.

This script automates the entire deployment process, including resource creation, database setup, and initial data collection.

## Features

- **Automated End-to-End Deployment**: One script handles everything from Azure resource creation to application deployment
- **Real-Time Weather Data**: Collects weather data for multiple cities worldwide using the Open-Meteo API (free, no API key required)
- **Comprehensive Analytics**: View temperature trends, min/max values, and averages
- **30-Day Historical Data**: Stores and displays weather patterns for the past month
- **Scheduled Data Collection**: Automatically refreshes data every 6 hours via Kubernetes CronJob
- **Responsive Dashboard**: Modern web interface for visualizing weather statistics
- **High Availability**: Deployed on Azure Kubernetes Service for reliability and scalability
- **Secure Database Integration**: Uses Azure SQL Database with proper credential management

## Architecture

The solution consists of several key components:

1. **Weather Data Service API**
   - Flask-based REST API for accessing weather data
   - Endpoints for cities, weather data, and analytics
   - CORS support for cross-domain access

2. **Database Layer**
   - Azure SQL Database for persistent storage
   - Native SQL queries for optimal performance (no ORM)
   - Tables for cities, weather data, and statistical aggregations

3. **Data Collection Service**
   - Automated collection from Open-Meteo API
   - Runs as a Kubernetes CronJob every 6 hours
   - Immediate data collection upon deployment
   - Fallback mechanisms for reliable operation

4. **Web Dashboard**
   - Interactive visualization of weather statistics
   - City selection and data filtering
   - Temperature trends and analytics display
   - Responsive design for all devices

## Automated Deployment Process

The `setup_azure_environment.ps1` script handles the entire deployment process:

1. **Azure Resource Creation**
   - Resource Group for organizing all components
   - AKS Cluster with appropriate node configuration
   - Azure SQL Server and Database with firewall rules
   - Azure Container Registry for Docker images

2. **Container Management**
   - Builds Docker images for the weather service
   - Pushes images to Azure Container Registry
   - Configures ACR authentication for AKS

3. **Kubernetes Deployment**
   - Deploys API service with load balancer
   - Sets up dashboard with ConfigMap for static files
   - Creates database setup job
   - Configures CronJob for regular data collection
   - Triggers immediate data collection

4. **Database Initialization**
   - Creates necessary database tables
   - Implements fallback mechanisms using sqlcmd
   - Sets up sample cities (Tel Aviv, Jerusalem, etc.)

5. **Security Configuration**
   - Creates Kubernetes secrets for database credentials
   - Configures proper ACR authentication
   - Sets up secure communication between components

## Technical Details

### Prerequisites

- Azure CLI installed and configured
- PowerShell 7.0 or later
- Docker Desktop installed and running
- Kubernetes CLI (kubectl) installed

### Deployment Instructions

1. Clone this repository
2. Navigate to the project directory
3. Run the deployment script:

```powershell
./setup_azure_environment.ps1
```

4. Wait for the deployment to complete (approximately 15-20 minutes)
5. Access the dashboard and API using the URLs provided in the deployment summary

## API Documentation

The Weather Data Service API provides the following endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /` | API documentation |
| `GET /cities` | List all cities |
| `GET /cities/<city_id>` | Get city details |
| `GET /weather/<city_id>` | Get weather data for a city |
| `GET /stats/<city_id>` | Get weather statistics for a city |
| `GET /hottest` | Get the hottest city |
| `GET /coldest` | Get the coldest city |
| `GET /windiest` | Get the windiest city |

### Database Schema

The solution uses a well-structured database schema:

1. **cities** - Stores city information
   - Primary data for locations being monitored
   - Includes geographic coordinates for API calls

2. **weather_data** - Stores daily weather records
   - 30 days of historical data per city
   - Comprehensive weather metrics (temperature, humidity, etc.)

3. **weather_stats** - Stores aggregated statistics
   - Pre-calculated analytics for efficient dashboard display
   - Both 7-day and 30-day aggregation periods

## Error Handling and Reliability

The system includes multiple reliability features:

- Fallback mechanisms for database initialization
- Multiple ACR authentication methods
- Automatic retry logic for API calls
- Comprehensive error logging
- Graceful handling of missing data

## Cleanup

To remove all Azure resources when you're done:

```powershell
az group delete --name weather-data-rg --yes
```

## Project Structure

- `/kubernetes/` - Kubernetes deployment manifests
- `/weather-dashboard-new/` - Frontend dashboard files (current version)
- `*.py` - Python scripts for data collection and API
- `Dockerfile` - Container definition
- `setup_azure_environment.ps1` - Main deployment script

## Contributors

This project was developed as part of a Microsoft technical assessment.

## License

This project is licensed under the MIT License.
