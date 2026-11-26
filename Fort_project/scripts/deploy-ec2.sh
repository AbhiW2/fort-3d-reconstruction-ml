#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ! "${IMAGE_TAG:-}" =~ ^sha-[a-f0-9]{40}$ ]]; then
  echo "IMAGE_TAG must be a published sha-<40-character-commit> tag." >&2
  exit 1
fi

if ! command -v docker >/dev/null; then
  echo "Docker is not installed on the EC2 instance." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is not available on the EC2 instance." >&2
  exit 1
fi

api_container=""
while IFS= read -r candidate; do
  service=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$candidate")
  image=$(docker inspect --format '{{.Config.Image}}' "$candidate")
  if [[ "$service" == "api" && ( "$image" == "fort-api:local" || "$image" == ghcr.io/abhiw2/fort-3d-reconstruction-ml-api:* ) ]]; then
    api_container="$candidate"
    break
  fi
done < <(docker ps -q)

if [[ -z "$api_container" ]]; then
  echo "Could not find a running Fort API container managed by Docker Compose." >&2
  echo "No containers were changed. Verify the current EC2 deployment uses the api service from Fort_project/compose.yaml." >&2
  exit 1
fi

project=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$api_container")
working_dir=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}' "$api_container")
config_files=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' "$api_container")

if [[ -z "$project" || -z "$working_dir" || -z "$config_files" || ! -d "$working_dir" ]]; then
  echo "The running API container is missing Docker Compose project metadata." >&2
  exit 1
fi
echo "Found Compose project '$project' in '$working_dir' using '$config_files'."

web_container=""
while IFS= read -r candidate; do
  service=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$candidate")
  candidate_project=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$candidate")
  if [[ "$service" == "web" && "$candidate_project" == "$project" ]]; then
    web_container="$candidate"
    break
  fi
done < <(docker ps -q)

if [[ -z "$web_container" ]]; then
  echo "Could not find the running web service in Compose project '$project'. No containers were changed." >&2
  exit 1
fi

compose_args=(--project-directory "$working_dir")
IFS=',' read -r -a files <<< "$config_files"
for file in "${files[@]}"; do
  if [[ "$file" != /* ]]; then
    file="$working_dir/$file"
  fi
  if [[ ! -f "$file" ]]; then
    echo "Compose file does not exist: $file" >&2
    exit 1
  fi
  compose_args+=(-f "$file")
done

override_file="$working_dir/.fort-ghcr-deploy.override.yaml"
old_api_image=$(docker inspect --format '{{.Config.Image}}' "$api_container")
old_web_image=$(docker inspect --format '{{.Config.Image}}' "$web_container")

write_override() {
  local api_image="$1"
  local web_image="$2"
  if [[ ! "$api_image" =~ ^[A-Za-z0-9._/:@-]+$ || ! "$web_image" =~ ^[A-Za-z0-9._/:@-]+$ ]]; then
    echo "An existing container has an invalid image reference; refusing to write a Compose override." >&2
    return 1
  fi
  cat > "$override_file" <<EOF
services:
  api:
    image: "$api_image"
  web:
    image: "$web_image"
EOF
}

api_image="ghcr.io/abhiw2/fort-3d-reconstruction-ml-api:${IMAGE_TAG}"
web_image="ghcr.io/abhiw2/fort-3d-reconstruction-ml-web:${IMAGE_TAG}"
write_override "$api_image" "$web_image"

compose() {
  docker compose "${compose_args[@]}" -f "$override_file" "$@"
}

compose config --quiet
compose pull api web

if ! compose up -d --no-build api web; then
  echo "Compose could not start the new images; attempting to restore the previous images." >&2
  write_override "$old_api_image" "$old_web_image"
  compose up -d --no-build api web
  exit 1
fi

healthy=0
for attempt in {1..36}; do
  api_id=$(compose ps -q api)
  web_id=$(compose ps -q web)
  if [[ -n "$api_id" && -n "$web_id" ]] \
    && docker exec "$api_id" python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/health', timeout=3)" >/dev/null 2>&1 \
    && docker exec "$web_id" nginx -t >/dev/null 2>&1; then
    healthy=1
    break
  fi
  sleep 5
done

if [[ "$healthy" -ne 1 ]]; then
  echo "The new deployment did not pass API/web health checks; attempting to restore the previous images." >&2
  compose logs --tail=80 api web || true
  write_override "$old_api_image" "$old_web_image"
  compose up -d --no-build api web
  exit 1
fi

echo "Deployed ${IMAGE_TAG} to Compose project '${project}'."
