# Nano settings

Creates simple python config from environment variables. Smaller analog of
pydantic-settings.

## In comparison with pydantic-settings

Pros:

* Easier to understand and support.
* Relies only on standard library.
* Uses dataclasses, not polluting your code with external types (if you're
  using approaches similar to clean architecture).
* Almost no configuration.

Cons:

* No validation, you have to do it yourself.
* Almost no configuration.

## Installation

```shell
pip install nano-settings
```

## Basic usage

```python
from dataclasses import dataclass

import nano_settings as ns


@dataclass
class DbSetup(ns.BaseConfig):
    max_sessions: int
    autocommit: bool = True


@dataclass
class Database(ns.BaseConfig):
    url: str
    timeout: int
    setup: DbSetup


# export MY_VAR__URL=https://site.com
# export MY_VAR__TIMEOUT=10
# export MY_VAR__SETUP__MAX_SESSIONS=2
config = ns.from_env(Database, env_prefix='my_var')
print(config)
# Database(timeout=10, url='https://site.com', setup=DbSetup(max_sessions=2, autocommit=True))
```

## Supported variants

### Straightforward - when your annotations are callable

```python
from dataclasses import dataclass

import nano_settings as ns


@dataclass
class Config(ns.BaseConfig):
    variable: int
    # equivalent of
    # variable = int(os.getenv('VARIABLE'))
```

### Annotated - when your annotations are complex and cannot be called

```python
from dataclasses import dataclass
from typing import Annotated
import json

import nano_settings as ns


@dataclass
class Config(ns.BaseConfig):
    variable: Annotated[list[int], lambda x: x['key'], json.loads]
    # equivalent of
    # variable = json.loads(os.getenv('VARIABLE'))['key']
```

### Nested - when your annotations are models

Example is listed in [Basic usage](#basic-usage)

## Aliases - when you want to get value by different name

### Normal - try default and then alternatives

```python
from dataclasses import dataclass
from typing import Annotated

import nano_settings as ns


@dataclass
class Config(ns.BaseConfig):
    variable: Annotated[str, ns.EnvAlias('OTHER')]
    # will try to get `VARIABLE` and then `OTHER`
```

### Strict - try only alternatives

```python
from dataclasses import dataclass
from typing import Annotated

import nano_settings as ns


@dataclass
class Config(ns.BaseConfig):
    variable: Annotated[str, ns.EnvAliasStrict('OTHER')]
    # will only try to get `OTHER`
```

### Nullable - if `null` is also a valid value

```python
from dataclasses import dataclass
from typing import Annotated

import nano_settings as ns


@dataclass
class Config(ns.BaseConfig):
    variable: Annotated[int | None, ns.Nullable(int)]
```
