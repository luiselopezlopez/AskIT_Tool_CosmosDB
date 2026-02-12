# Script para desplegar AskIT en Azure
# Requiere: Azure CLI, Docker

$ErrorActionPreference = "Stop" # Detener en caso de error

# Deploy Configuratin Parameters
$acrName = "askitdevacr" # update with your Azure Container Registry name (must be unique across Azure)
$imageName = "askit-mcp-cosmosdb" # name of the Docker image to build and push
# Constants
$acrLoginServer = "$acrName.azurecr.io"

# Función para manejar errores y salir del script
function Handle-Error {
    param (
        [string]$ErrorMessage
    )
    
    Write-Host "ERROR: $ErrorMessage" -ForegroundColor Red
    exit 1
}

# Iniciar sesión en Azure
Write-Host "Benvenido al script de despliegue de AskIT en Azure" -ForegroundColor Green
Write-Host "Asegúrate de tener Azure CLI y Docker instalados y configurados." -ForegroundColor Yellow
Pause
Write-Host "Iniciando sesión en Azure..." -ForegroundColor Cyan
#az login

# Iniciar sesión en el ACR
Write-Host "Iniciando sesión en el ACR..." -ForegroundColor Cyan
try {
    $result = az acr login --name $acrName
    if (-not $result) { Handle-Error "No se pudo iniciar sesión en el ACR" }
} catch {
    Handle-Error "Error al iniciar sesión en el ACR: $_"
}

# Obtener la siguiente versión
try {
    $version = Get-Date -Format "yyyyMMddhhmm"
    Write-Host "Nueva versión: $version" -ForegroundColor Green
} catch {
    Handle-Error "Error al obtener la siguiente versión: $_"
}

# Construir la imagen Docker
Write-Host "Construyendo imagen Docker..." -ForegroundColor Cyan
try {
    docker build -t "$imageName`:$version" .
    if ($LASTEXITCODE -ne 0) { Handle-Error "Error al construir la imagen Docker" }
} catch {
    Handle-Error "Error al construir la imagen Docker: $_"
}

# Etiquetar la imagen para el ACR
Write-Host "Etiquetando imagen para ACR..." -ForegroundColor Cyan
try {
    docker tag "$imageName`:$version" "$acrLoginServer/$imageName`:$version"
    if ($LASTEXITCODE -ne 0) { Handle-Error "Error al etiquetar la imagen con versión" }
    
    docker tag "$imageName`:$version" "$acrLoginServer/$imageName`:latest"
    if ($LASTEXITCODE -ne 0) { Handle-Error "Error al etiquetar la imagen como latest" }
} catch {
    Handle-Error "Error al etiquetar la imagen: $_"
}

# Subir la imagen al ACR
Write-Host "Subiendo imagen al ACR..." -ForegroundColor Cyan
try {
    docker push "$acrLoginServer/$imageName`:$version"
    if ($LASTEXITCODE -ne 0) { Handle-Error "Error al subir la imagen con versión al ACR" }
    
    docker push "$acrLoginServer/$imageName`:latest"
    if ($LASTEXITCODE -ne 0) { Handle-Error "Error al subir la imagen latest al ACR" }
} catch {
    Handle-Error "Error al subir la imagen al ACR: $_"
}


