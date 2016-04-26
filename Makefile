DEST := .

.DEFAULT: test
test: 
	tox

.PHONY: clean

clean:
	rm -rf $(DEST)/dist
	rm -rf $(DEST)/build
	rm -rf $(DEST)/dynamo_objects.egg-info

setup:
	pip install -r requirements.txt
	pip install -r requirements_dev.txt

version:
	bumpversion patch

publish: clean test
	python setup.py checkdocs
	python setup.py sdist
	# python setup.py bdist_wheel
	twine upload dist/*
	# @echo "Run the following commands to tag the version:"
	# @python -c "print \"  git tag -a {0} -m 'version {0}'\".format(__import__('dynamo_objects').__version__)"
	@echo "Run the following commands to tag the version:"
	@echo "  bumpversion [patch|minor|major]"
	@echo "  git push --tags"
