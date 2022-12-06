#!/usr/bin/env bash

conan remove "*" -c
conan cci:export-all-versions --list=.github/top_100_recipes.yaml
conan cci:create-top-versions --list=.github/top_100_recipes.yaml
