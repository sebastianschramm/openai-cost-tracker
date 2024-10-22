# openai-cost-tracker

[![PyPI version](https://badge.fury.io/py/openai-request-tracker.svg)](https://badge.fury.io/py/openai-request-tracker)
[![Build Status](https://github.com/sebastianschramm/openai-cost-tracker/actions/workflows/python-publish.yml/badge.svg)](https://github.com/sebastianschramm/openai-cost-tracker/actions)
[![GitHub](https://img.shields.io/badge/source-GitHub-blue)](https://github.com/sebastianschramm/openai-cost-tracker)

Cost tracker that logs OpenAI requests using opentelemetry. Once enabled, it will log every request that
is being made via the openai python client to a file in the execution directory. The log file is
called "traces_<\datetime>.log".

## Installation

### Install from PYPI

```bash
pip install openai-request-tracker
```

Please note the difference between pypi package name and github repository name.

### Install from source

Install with poetry:

```bash
poetry install
```

or install with pip:

```bash
pip install .
```

## Usage

### Record requests

#### CLI wrapper

The command **track-costs** is a wrapper that initializes the tracker and then runs the given CLI command.

```bash
track-costs <your usual command>
```

For example, if your are running usually an indexing run with [microsoft/graphRAG](https://github.com/microsoft/graphrag)
with

```bash
python -m graphrag.index --root foo
```

you only need to change it to

```bash
track-costs graphrag.index --root foo
```

to record all openai requests in a log file.

Similarly, for calling the graphrag query module you can do

```bash
track-costs graphrag.query --root foo --method local "My query"
```

#### In code usage

You can just add a call to cost_tracker.init_tracker() at the very beginning of your script:

```python

from cost_tracker import init_tracker

init_tracker()

... # your script

```

For example, to make it work for the indexing phase of [microsoft/graphRAG](https://github.com/microsoft/graphrag), modify the file [main.py](https://github.com/microsoft/graphrag/blob/main/graphrag/index/__main__.py) such that it looks like:

```python
# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""The Indexing Engine package root."""
from cost_tracker import init_tracker

init_tracker()

import argparse

from graphrag.logging import ReporterType
from graphrag.utils.cli import dir_exist, file_exist

from .cli import index_cli
from .emit.types import TableEmitterType


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="python -m graphrag.index",
        description="The graphrag indexing engine",
    )

... # rest of the unmodified script

```

Run your script as before.

### Show costs

The script "display-costs" can be used to show the openai costs for all requests recorded in a given log file:

```bash
display-costs --file <YOUR_LOG_FILE>
```
