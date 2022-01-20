@echo off
TITLE Releasing the library
echo Installing dependencies...
pip install -r requirements-dev.txt
echo Bumping up library version...
bumpversion --current-version 0.0.0 minor setup.py telegram/__init__.py run.bat
echo Building the package...
python setup.py sdist bdist_wheel
echo Uploading the package...
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
del /Q dist
echo All Done!