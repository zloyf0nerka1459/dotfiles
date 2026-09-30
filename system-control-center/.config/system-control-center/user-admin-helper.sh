#!/usr/bin/env bash
# ==============================================================================
# System Control Center — User Administration Helper
# Used by system_control_center.py to manage system accounts safely
# ==============================================================================
set -euo pipefail

# Ensure running as root (or through pkexec / sudo)
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This helper must be run as root." >&2
    exit 1
fi

ACTION="${1:-}"

case "$ACTION" in
    create)
        USERNAME="${2:-}"
        FULLNAME="${3:-}"
        USER_SHELL="${4:-/bin/bash}"
        IS_ADMIN="${5:-0}"
        PASSWORD="${6:-}"

        if [ -z "$USERNAME" ]; then
            echo "ERROR: Username is required." >&2
            exit 1
        fi

        # Check if user already exists
        if id "$USERNAME" >/dev/null 2>&1; then
            echo "ERROR: User '$USERNAME' already exists." >&2
            exit 2
        fi

        # Create user with home directory and full name
        useradd -m -c "$FULLNAME" -s "$USER_SHELL" "$USERNAME"

        # Standard desktop groups so sound, video, input and gaming work out of the box
        for grp in audio video input storage optical games render; do
            if getent group "$grp" >/dev/null 2>&1; then
                usermod -aG "$grp" "$USERNAME" 2>/dev/null || true
            fi
        done

        # Admin / Sudo privileges
        if [ "$IS_ADMIN" = "1" ]; then
            if getent group wheel >/dev/null 2>&1; then
                usermod -aG wheel "$USERNAME"
            elif getent group sudo >/dev/null 2>&1; then
                usermod -aG sudo "$USERNAME"
            fi
        fi

        # Set password if provided
        if [ -n "$PASSWORD" ]; then
            echo "$USERNAME:$PASSWORD" | chpasswd
        fi

        echo "SUCCESS: User '$USERNAME' created successfully."
        ;;

    delete)
        USERNAME="${2:-}"
        DELETE_HOME="${3:-0}"

        if [ -z "$USERNAME" ]; then
            echo "ERROR: Username is required." >&2
            exit 1
        fi

        # Safety protections
        if [ "$USERNAME" = "root" ] || [ "$USERNAME" = "fonera" ]; then
            echo "ERROR: Cannot delete protected system account '$USERNAME'." >&2
            exit 3
        fi

        # Kill any active processes belonging to the user before deleting
        pkill -u "$USERNAME" 2>/dev/null || true
        sleep 0.2

        if [ "$DELETE_HOME" = "1" ]; then
            userdel -r "$USERNAME"
        else
            userdel "$USERNAME"
        fi

        echo "SUCCESS: User '$USERNAME' deleted successfully."
        ;;

    toggle-admin)
        USERNAME="${2:-}"
        ENABLE="${3:-0}"

        if [ -z "$USERNAME" ]; then
            echo "ERROR: Username is required." >&2
            exit 1
        fi

        if [ "$ENABLE" = "1" ]; then
            if getent group wheel >/dev/null 2>&1; then
                usermod -aG wheel "$USERNAME"
            fi
            echo "SUCCESS: Admin privileges granted to '$USERNAME'."
        else
            if [ "$USERNAME" = "fonera" ]; then
                echo "ERROR: Cannot revoke admin rights from primary system user 'fonera'." >&2
                exit 4
            fi
            if getent group wheel >/dev/null 2>&1; then
                gpasswd -d "$USERNAME" wheel 2>/dev/null || true
            fi
            echo "SUCCESS: Admin privileges revoked from '$USERNAME'."
        fi
        ;;

    set-password)
        USERNAME="${2:-}"
        PASSWORD="${3:-}"

        if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
            echo "ERROR: Username and password are required." >&2
            exit 1
        fi

        echo "$USERNAME:$PASSWORD" | chpasswd
        echo "SUCCESS: Password for '$USERNAME' updated successfully."
        ;;

    set-fullname)
        USERNAME="${2:-}"
        FULLNAME="${3:-}"

        if [ -z "$USERNAME" ]; then
            echo "ERROR: Username is required." >&2
            exit 1
        fi

        usermod -c "$FULLNAME" "$USERNAME"
        echo "SUCCESS: Full name for '$USERNAME' updated successfully."
        ;;

    *)
        echo "Usage: $0 {create|delete|toggle-admin|set-password|set-fullname} [args...]" >&2
        exit 1
        ;;
esac
