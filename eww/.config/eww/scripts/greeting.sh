#!/bin/bash
USER=$(whoami)
GREETINGS=("Привет, $USER!" "Как дела, $USER?" "Снова за Arch, $USER?" "Время делать миксы!")
RANDOM_INDEX=$((RANDOM % ${#GREETINGS[@]}))
echo "${GREETINGS[$RANDOM_INDEX]}"
