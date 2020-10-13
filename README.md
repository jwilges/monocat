<p align="center">
  <a href="https://github.com/jwilges/monocat" title="monocat">
    <img src="https://raw.githubusercontent.com/jwilges/monocat/master/docs/logo-300px.png" alt="a monocat in a box" width="150px" height="150px">
  </a>
</p>

# monocat
*`monocat`: a simple standalone command line interface for managing GitHub releases and release assets.*

[![build](https://img.shields.io/azure-devops/build/jwilges/monocat/1/master)](https://jwilges.visualstudio.com/monocat/_build?definitionId=1)
[![tests](https://img.shields.io/azure-devops/tests/jwilges/monocat/1/master?compact_message)](https://jwilges.visualstudio.com/monocat/_test/analytics?definitionId=1&contextType=build)
![coverage](https://img.shields.io/azure-devops/coverage/jwilges/monocat/1/master)
![license](https://img.shields.io/github/license/jwilges/monocat)
![pypi python versions](https://img.shields.io/pypi/pyversions/monocat)
[![pypi release](https://img.shields.io/pypi/v/monocat)](https://pypi.org/project/monocat)
![pypi monthly downloads](https://img.shields.io/pypi/dm/monocat)

## Background
This utility aims to make integrating GitHub release steps in CI/CD pipelines simple.

## Supported Platforms
This utility is continuously unit tested on a GNU/Linux system with Python 3.6, 3.7, and 3.8.

## Usage
Use the `GITHUB_API` environment variable to specify alternate GitHub API URLs;
the default value is [https://api.github.com](https://api.github.com).

## Prior Art
This utility was inspired by the [`gothub`](https://github.com/itchio/gothub)
utility from [itch.io](https://github.com/itchio). As their utility has been
archived/deprecated without one clear path forward, this project aims to fill in
as a "close enough" successor.