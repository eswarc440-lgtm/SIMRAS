#!/usr/bin/env sh
set -eu

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Review its secrets before deployment."
fi

docker compose up --build -d
docker compose ps
echo "Frontend: http://localhost:5173"
echo "Swagger:  http://localhost:8000/docs"

