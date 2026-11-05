#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

verify=true
install_only=false
setup_args=()
while (( $# > 0 )); do
    case "$1" in
        --skip-verify) verify=false; shift ;;
        --install-only) install_only=true; shift ;;
        --help|-h)
            cat <<'HELP'
Usage: bash scripts/setup-ubuntu.sh [--bind PRIVATE_IP | --local] [--skip-verify] [--install-only]

One entry point: install missing Docker/host tools, generate local secrets,
detect a dedicated private interface, seed PostgreSQL, start the web services,
and run verification. Existing .env credentials and databases are preserved.
VM creation and virtual network adapter configuration are separate prerequisites.
HELP
            exit 0 ;;
        --bind)
            (( $# >= 2 )) || { echo '--bind requires an IP address' >&2; exit 2; }
            setup_args+=(--bind "$2"); shift 2 ;;
        --local) setup_args+=(--local); shift ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done

bash scripts/install_docker_ubuntu.sh --install-only
if [[ "$install_only" == true ]]; then exit 0; fi
if ! docker info >/dev/null 2>&1; then
    if ! sudo -n docker info >/dev/null 2>&1; then sudo -v; fi
    sudo -n docker info >/dev/null
    export MINISHOP_DOCKER_SUDO=1
fi
if [[ "$verify" == true ]]; then setup_args+=(--verify); fi
exec python3 scripts/setup.py "${setup_args[@]}"
