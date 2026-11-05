#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
    cat <<'EOF'
Usage: bash scripts/install_docker_ubuntu.sh [--install-only]

Install missing host tools and Docker Engine/Compose on Ubuntu LTS.
Existing runtimes and project data are preserved. Internet access is required.

Options:
  --install-only  Prepare Docker without starting the application.
  -h, --help      Show this help.
EOF
}

install_only=false
case "${1:-}" in
    '') ;;
    --install-only) install_only=true ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
esac
if (( $# > 1 )); then
    usage >&2
    exit 2
fi

die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
trap 'printf "Setup stopped at line %s. Resolve the error above and run this script again.\n" "$LINENO" >&2' ERR

[[ -r /etc/os-release ]] || die 'Run this script inside an Ubuntu 24.04 VM.'
# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == ubuntu && ( "${VERSION_ID:-}" == 24.04 || "${VERSION_ID:-}" == 26.04 ) ]] || \
    die 'Run this installer inside an Ubuntu 24.04 or 26.04 LTS VM.'

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$project_dir"
[[ -f docker-compose.yml ]] || die 'The renewal docker-compose.yml is missing.'

# Only the local Ubuntu Engine is managed. Do not change a remote daemon.
[[ -z "${DOCKER_HOST:-}" || "${DOCKER_HOST}" == unix:///var/run/docker.sock ]] || \
    die 'Unset DOCKER_HOST to use the local Ubuntu Docker Engine.'
[[ -z "${DOCKER_CONTEXT:-}" || "${DOCKER_CONTEXT}" == default ]] || \
    die 'Unset DOCKER_CONTEXT to use the local Ubuntu Docker Engine.'
if command -v docker >/dev/null 2>&1; then
    current_context="$(docker context show)"
    [[ "$current_context" == default ]] || \
        die 'Select the local Engine with "docker context use default" before running setup.'
fi

privilege=()
sudo_ready=false
require_admin() {
    if (( EUID != 0 )) && [[ "$sudo_ready" != true ]]; then
        command -v sudo >/dev/null 2>&1 || die 'sudo is required; run setup as an administrator.'
        if ! sudo -n true 2>/dev/null; then
            sudo -v
        fi
        privilege=(sudo)
        sudo_ready=true
    fi
}

package_installed() {
    [[ "$(dpkg-query -W -f='${Status}' "$1" 2>/dev/null || true)" == 'install ok installed' ]]
}

host_packages=()
for host_command in python3 git curl; do
    if ! command -v "$host_command" >/dev/null 2>&1; then host_packages+=("$host_command"); fi
done
if (( ${#host_packages[@]} > 0 )); then
    require_admin
    "${privilege[@]}" apt-get update
    "${privilege[@]}" apt-get install -y --no-remove --no-install-recommends "${host_packages[@]}" ca-certificates
fi

packages=()
if ! command -v docker >/dev/null 2>&1; then
    # Do not let apt replace an existing distribution/custom container runtime.
    for conflicting in docker.io docker-compose docker-compose-v2 docker-doc \
                       podman-docker containerd runc; do
        if package_installed "$conflicting"; then
            die "Existing package '$conflicting' requires manual Docker configuration; nothing was removed."
        fi
    done
    for required in docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; do
        if ! package_installed "$required"; then packages+=("$required"); fi
    done
else
    if ! docker compose version >/dev/null 2>&1; then packages+=(docker-compose-plugin); fi
    if ! docker buildx version >/dev/null 2>&1; then packages+=(docker-buildx-plugin); fi
    if (( ${#packages[@]} > 0 )) && ! package_installed docker-ce; then
        die 'An existing non-Docker-CE installation lacks Compose or Buildx. Install its matching plugins manually; the existing Engine was not replaced.'
    fi
fi

key_file=''
trap 'if [[ -n "$key_file" ]]; then rm -f -- "$key_file"; fi' EXIT
if (( ${#packages[@]} > 0 )); then
    require_admin
    printf 'Installing missing Docker components from the official Ubuntu repository.\n'

    # Keep existing repository configuration instead of duplicating signed sources.
    if ! grep -qs 'https://download.docker.com/linux/ubuntu' \
        /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; then
        [[ ! -e /etc/apt/sources.list.d/docker.sources ]] || \
            die '/etc/apt/sources.list.d/docker.sources already exists; review it before setup.'
        "${privilege[@]}" apt-get update
        "${privilege[@]}" apt-get install -y --no-remove --no-install-recommends ca-certificates curl
        "${privilege[@]}" install -m 0755 -d /etc/apt/keyrings
        key_file="$(mktemp)"
        curl -fsSL --retry 3 --connect-timeout 15 \
            https://download.docker.com/linux/ubuntu/gpg -o "$key_file"
        "${privilege[@]}" install -m 0644 "$key_file" /etc/apt/keyrings/docker.asc
        rm -f -- "$key_file"
        key_file=''
        printf '%s\n' \
            'Types: deb' \
            'URIs: https://download.docker.com/linux/ubuntu' \
            "Suites: ${VERSION_CODENAME}" \
            'Components: stable' \
            "Architectures: $(dpkg --print-architecture)" \
            'Signed-By: /etc/apt/keyrings/docker.asc' | \
            "${privilege[@]}" tee /etc/apt/sources.list.d/docker.sources >/dev/null
    fi

    "${privilege[@]}" apt-get update
    "${privilege[@]}" apt-get install -y --no-remove --no-install-recommends "${packages[@]}"
fi

command -v docker >/dev/null 2>&1 || die 'Docker CLI is unavailable after installation.'
docker compose version >/dev/null 2>&1 || die 'Docker Compose plugin is unavailable.'
docker buildx version >/dev/null 2>&1 || die 'Docker Buildx plugin is unavailable.'

docker_command=(docker)
if ! docker info >/dev/null 2>&1; then
    require_admin
    docker_command=("${privilege[@]}" docker)
    if ! "${docker_command[@]}" info >/dev/null 2>&1; then
        [[ -d /run/systemd/system ]] && command -v systemctl >/dev/null 2>&1 || \
            die 'The local Docker Engine is unavailable. Start it on an Ubuntu VM running systemd.'
        printf 'Starting the local Docker Engine.\n'
        "${privilege[@]}" systemctl enable --now docker
        "${docker_command[@]}" info >/dev/null 2>&1 || die 'The Docker Engine did not become ready.'
    fi
fi

"${docker_command[@]}" --version
"${docker_command[@]}" compose version
printf 'Host tools and Docker are ready. Existing project data was preserved.\n'
