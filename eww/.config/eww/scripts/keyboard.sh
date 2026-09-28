#!/usr/bin/env bash
layout=$(xkblayout-state print "%s" 2>/dev/null || echo "us")
echo "${layout^^}"
