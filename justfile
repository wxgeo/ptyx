default:
    just --list
    
    
doc:
    uv run make -C doc autodoc
    uv run make -C doc html
    
test:
    uv run ruff check ptyx tests
    uv run mypy ptyx tests
    uv run pytest tests ptyx/extensions

update-version:
    uv run semantic-release version
	
build: update-version
    uv build
    
publish: build
    uv publish
	
fix:
    uv run black .
    uv run ruff check --fix ptyx tests
    
lock:
    git commit uv.lock -m "dev: update uv.lock"
