

This repository contains a small hook for [pre-commit](https://pre-commit.com)
for creating a [Gerrit](https://www.gerritcodereview.com/)-compatible
`Change-Id` tag in [git](https://git-scm.com/) commit messages.

## Hacking

You'll want to install the developer dependencies:

```
pip install -e .[develop]
```

This will include `nose2`, which is the test runner of choice. After you make modifications you can run tests with

```
nose2
```

When you're satisfied you'll want to update the version number and do build-and-upload:

```
python setup.py sdist bdist_wheel
twine upload dist/* --verbose
```
