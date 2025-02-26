help:
	cat Makefile

doc: .
	poetry run make -C doc autodoc
	poetry run make -C doc html

tox:
	black .
	poetry run tox

version:
	poetry run semantic-release version

build: version
	poetry build

publish: build
	poetry publish
	
fix:
	poetry run black .
	poetry run ruff check --fix ptyx tests

lock:
	git commit poetry.lock -m "dev: update poetry.lock"
