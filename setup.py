"Logic for installing the module."
import setuptools # type: ignore

setuptools.setup(
	install_requires=[
		"precommit-message-preservation==0.6",
	],
	extras_require={
		"develop": [
			"mypy",
			"nose2",
			"pylint",
			"twine",
			"wheel",
		]
	},
)
