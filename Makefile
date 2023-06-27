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

build:
	poetry build

publish:
	poetry publish --build
