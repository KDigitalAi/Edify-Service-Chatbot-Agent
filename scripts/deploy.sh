#!/usr/bin/env bash
set -euo pipefail

# Usage:
#  ./scripts/deploy.sh dev      -> uses docker-compose.yml with project edify_dev (port 8080)
#  ./scripts/deploy.sh prod     -> uses docker-compose.prod.yml with project edify_prod (port 8081)
#  ./scripts/deploy.sh dev -n   -> dry run (no up)
#
ENV=${1:-dev}
DRY_RUN=false
if [ "${2:-}" = "-n" ] || [ "${2:-}" = "--dry-run" ]; then
  DRY_RUN=true
fi

ROOT_DIR="$(dirname "$(readlink -f "$0")")/.."
cd "$ROOT_DIR"

echo "Deploy script starting for environment: $ENV"
echo "Working dir: $(pwd)"

# check docker
if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker not available. Exiting."
  exit 1
fi

# verify .env
if [ ! -f .env ]; then
  echo "ERROR: .env not found in $ROOT_DIR. Create it and try again."
  exit 1
fi

# select compose file and project name
if [ "$ENV" = "prod" ]; then
  COMPOSE_FILE="docker-compose.prod.yml"
  PROJECT="edify_prod"
  HEALTH_URL="http://localhost:8081/health"
else
  COMPOSE_FILE="docker-compose.yml"
  PROJECT="edify_dev"
  HEALTH_URL="http://localhost:8080/health"
fi

echo "Using compose: $COMPOSE_FILE"
echo "Project name: $PROJECT"

# git pull latest for that branch
if [ "$ENV" = "prod" ]; then
  GIT_BRANCH="main"
else
  GIT_BRANCH="dev"
fi

echo "Fetching and resetting to origin/$GIT_BRANCH"
git fetch origin
git reset --hard "origin/$GIT_BRANCH"

# stop only this project's containers (safe)
echo "Stopping existing containers for project $PROJECT..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" down --remove-orphans || true

# build & start
if [ "$DRY_RUN" = true ]; then
  echo "Dry run enabled; skipping build/up."
  exit 0
fi

echo "Building images..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" build

echo "Starting containers..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" up -d --force-recreate

echo "Waiting for health endpoint: $HEALTH_URL"
sleep 5
if curl -f "$HEALTH_URL" >/dev/null 2>&1; then
  echo "Application healthy at $HEALTH_URL"
else
  echo "Warning: Health check failed (may take longer to start). Showing last logs..."
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT" logs --tail 50
fi

echo "Deployment finished for $ENV (project $PROJECT)."
