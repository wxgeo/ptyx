set shell := ["bash", "-cu"]

uv := "env -u VIRTUAL_ENV uv"
project := "ptyx"

default:
    just --list
    
    
sync:
   {{uv}} run sync
   
doc:
    {{uv}} run make -C doc autodoc
    {{uv}} run make -C doc html

ruff:
    {{uv}} run ruff check {{project}} tests

mypy: 
    {{uv}} run mypy {{project}} tests

pytest:
    {{uv}} run pytest tests ptyx/extensions
    
test: ruff mypy pytest

push:
    git push
    git push --tags
    
version:
    {{uv}} run semantic-release --noop version

update-version:
    {{uv}} run semantic-release version
	
build-new-version: update-version
    {{uv}} build
    
publish: build-new-version
    {{uv}} publish
	
fix:
    {{uv}} run black .
    {{uv}} run ruff check --fix {{project}} tests
    
lock:
    git commit uv.lock -m "dev: update uv.lock"
