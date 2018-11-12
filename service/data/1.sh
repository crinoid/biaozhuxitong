#!/usr/bin/env bash
cat "dict.txt" | awk -F ' ' '{print $1}' > o