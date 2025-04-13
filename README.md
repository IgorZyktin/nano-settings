# Nano settings

Creates simple python config from environment variables. Smaller analog of pydantic-settings.

## Installation

```shell
pip install nano-settings
```

## Usage

```python
from dataclasses import dataclass

from nano_settings import BaseConfig, from_env


@dataclass
class DbSetup(BaseConfig):
    max_sessions: int
    autocommit: bool = True


@dataclass
class Database(BaseConfig):
    url: str
    timeout: int
    setup: DbSetup


# export MY_VAR__URL=https://site.com
# export MY_VAR__TIMEOUT=10
# export MY_VAR__SETUP__MAX_SESSIONS=2
config = from_env(Database, env_prefix='my_var')
print(config)
# Database(timeout=10, url='https://site.com', setup=DbSetup(max_sessions=2, autocommit=True))
```
