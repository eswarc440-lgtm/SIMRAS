$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Review its secrets before deployment."
}

docker compose up --build -d
docker compose ps

Write-Host "SIMRAS is starting."
Write-Host "Frontend: http://localhost:5173"
Write-Host "Swagger:  http://localhost:8000/docs"

