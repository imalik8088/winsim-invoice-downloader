#!/usr/bin/env zsh

source ./venv/bin/activate

echo $(python --version)
echo $(type python)

cd fetchinvoice

set -ex
scrapy crawl winsim $@;
