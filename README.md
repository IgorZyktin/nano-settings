# Nano settings

Creates simple python config from environment variables. Smaller analog of
pydantic-settings.

## Installation

```shell
pip install nano-settings
```

## Usage

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

### Aliases - when you want to get value by different name

#### Normal - try default and then alternatives

```python
@dataclass
class DbSetup(ns.BaseConfig):
    variable: Annotated[str, ns.EnvAlias('OTHER')]
    # will try to get `VARIABLE` and then `OTHER`
```

#### Strict - try only alternatives

```python
@dataclass
class DbSetup(ns.BaseConfig):
    variable: Annotated[str, ns.EnvAliasStrict('OTHER')]
    # will only try to get `OTHER`
```
