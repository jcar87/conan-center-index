# Contributing to Conan Center Index

The following summarizes the process for contributing to the CCI (Conan Center Index) project.

<!-- toc -->
## Contents

  * [Community](#community)
  * [Dev-flow & Pull Requests](#dev-flow--pull-requests)
  * [Issues](#issues)<!-- endToc -->

## Community

The `conan-center-index` repository is an Open Source MIT licensed project; it is developed by the Conan maintainers and a great community of contributors. The CI infrastructure is provided and maintained by the Conan team at JFrog.

## Issues

If you experience issues when consuming recipes from Conan Center, you are encouraged to report them in our [issue tracker](https://github.com/conan-io/conan-center-index/issues/new).

Please ensure that the following information is part of the report:
- Conan version, operating system and version (output of `conan version`)
- The command you are trying to run, e.g. `conan install --require=boost/1.85.0`
- Any additional files required to reproduce your issue, where relevant:
   - Conan profile (you can attach the output of `conan profile show`, with the relevant profile flags)
   - A `conanfile.py` if you are using it to specify dependencies and options
- The outcome you expected
- The outcome you got instead (please include the full output log)

## Pull requests

We accept pull requests for bugfixes, new features in existing recipes, publish new versions for existing recipes, and to publish new recipes. 

Please ensure pull requests **clear, single primary purpose**, and that the changes in the PR are the minimal required to achieve that purpose. This makes them easier to review and ensures that one set of changes don't delay the merging of the others. With that in mind, please also avoid unrelated changes such as reformatting or refactoring code - unless it is required for the purpose of the PR. Correcting typos is welcome and appreciated.

Please keep the following in mind:

- For a bugfix PR, we will only consider PRs for confirmed bugs - anybody in


### Contributor License Agreement
 [contributor licenses agreement](https://cla-assistant.io/conan-io/conan-center-index).

