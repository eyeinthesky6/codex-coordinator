#!/bin/sh

set -u

hook_path=${1:-}
no_install=${2:-}
python_bin=

notice() {
    printf '%s\n' "Codex Coordinator: $1" >&2
}

try_python() {
    candidate=$1
    [ -n "$candidate" ] || return 1
    [ -x "$candidate" ] || return 1
    if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
        python_bin=$candidate
        return 0
    fi
    return 1
}

find_python() {
    for name in python3 python; do
        candidate=$(command -v "$name" 2>/dev/null || true)
        try_python "$candidate" && return 0
    done

    for candidate in \
        /opt/homebrew/bin/python3 \
        /usr/local/bin/python3 \
        /usr/bin/python3 \
        "$HOME"/.local/bin/python3 \
        "$HOME"/.cache/codex-runtimes/*/dependencies/python/bin/python3 \
        "$HOME"/.cache/codex-runtimes/*/dependencies/python/bin/python; do
        try_python "$candidate" && return 0
    done
    return 1
}

emit_missing_python() {
    detail=$1
    printf '%s' '{"continue":true,"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"Codex Coordinator could not start because Python 3.10 or newer was not found. '
    printf '%s' "$detail"
    printf '%s' ' Install Python 3.10+ and start a new Codex task; no environment setting was changed."}}'
}

if [ -z "$hook_path" ]; then
    emit_missing_python "The packaged hook path is missing."
    exit 0
fi

find_python || true
if [ -z "$python_bin" ] && [ "$no_install" != "--no-install" ]; then
    notice "Python 3.10+ was not found in PATH, standard install folders, or Codex runtime folders. Attempting a user-scoped or system-authorised Python install now."
    if command -v uv >/dev/null 2>&1; then
        uv python install 3.13 >&2 || true
        candidate=$(uv python find 3.13 2>/dev/null || true)
        try_python "$candidate" || true
    elif command -v brew >/dev/null 2>&1; then
        brew install python@3.13 >&2 || true
    elif [ "$(id -u)" = "0" ] && command -v apt-get >/dev/null 2>&1; then
        apt-get update >&2 && apt-get install -y python3 >&2 || true
    elif [ "$(id -u)" = "0" ] && command -v dnf >/dev/null 2>&1; then
        dnf install -y python3 >&2 || true
    fi
    [ -n "$python_bin" ] || find_python || true
fi

if [ -z "$python_bin" ]; then
    if [ "$no_install" = "--no-install" ]; then
        emit_missing_python "Automatic installation was disabled for this check."
    else
        emit_missing_python "No supported installer was available, or installation failed."
    fi
    exit 0
fi

exec "$python_bin" "$hook_path"
