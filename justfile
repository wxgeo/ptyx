set shell := ["bash", "-cu"]

uv := "env -u VIRTUAL_ENV uv"

default:
    just --list
    
    
sync:
   {{uv}} run sync
   
doc:
    {{uv}} run make -C doc autodoc
    {{uv}} run make -C doc html

ruff:
    {{uv}} run ruff check ptyx tests

mypy: 
    {{uv}} run mypy ptyx tests

pytest:
    {{uv}} run pytest tests ptyx/extensions
    
test: ruff mypy pytest


update-version:
    {{uv}} run semantic-release version
	
build: update-version
    {{uv}} build
    
publish: build
    {{uv}} publish
	
fix:
    {{uv}} run black .
    {{uv}} run ruff check --fix ptyx tests
    
lock:
    git commit uv.lock -m "dev: update uv.lock"
