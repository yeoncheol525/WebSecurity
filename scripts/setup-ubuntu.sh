#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

install_only=false
setup_args=()
while (( $# > 0 )); do
    case "$1" in
        --skip-verify) shift ;; # Compatibility: setup never runs verification now.
        --install-only) install_only=true; shift ;;
        --help|-h)
            cat <<'HELP'
Usage: bash scripts/setup-ubuntu.sh [--experiment E1|E2|E3|E4|A|C2] [--bind PRIVATE_IP | --local] [--install-only]

Install missing host tools, generate local settings, seed PostgreSQL,
and start the selected MiniShop services.
The first run uses E4; later runs keep the selected experiment.
Existing .env credentials and databases are preserved.
VM creation and virtual network adapter configuration are separate prerequisites.
HELP
            exit 0 ;;
        --bind)
            (( $# >= 2 )) || { echo '--bind requires an IP address' >&2; exit 2; }
            setup_args+=(--bind "$2"); shift 2 ;;
        --experiment)
            (( $# >= 2 )) || { echo '--experiment requires E1, E2, E3, E4, A or C2' >&2; exit 2; }
            case "$2" in E1|E2|E3|E4|A|C2) ;; *) echo 'Choose E1, E2, E3, E4, A or C2' >&2; exit 2 ;; esac
            setup_args+=(--experiment "$2"); shift 2 ;;
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
exec python3 scripts/setup.py "${setup_args[@]}"
