"""Tests."""

from dataclasses import dataclass
import json
from typing import Annotated
from typing import Any
from unittest import mock
from unittest.mock import patch

import pytest

from nano_settings.src import BaseConfig
from nano_settings.src import Boolean
from nano_settings.src import Choices
from nano_settings.src import ConfigValidationError
from nano_settings.src import EnvAlias
from nano_settings.src import EnvAliasStrict
from nano_settings.src import Interval
from nano_settings.src import Nullable
from nano_settings.src import SecretStr
from nano_settings.src import Separated
from nano_settings.src import from_env


def test_base_config_easy():
    """Must create config instance from env vars."""

    # arrange
    @dataclass
    class EasyConfig(BaseConfig):
        variable_1: int
        variable_2: str
        variable_3: bool = False

    # act
    with patch.dict(
        'os.environ',
        EASYCONFIG__VARIABLE_1='1',
        EASYCONFIG__VARIABLE_2='string',
    ):
        config = from_env(EasyConfig)

    # assert
    assert config.variable_1 == 1
    assert config.variable_2 == 'string'
    assert not config.variable_3


def test_base_config_skipped_unset():
    """Must fail to create because we have unset parameter."""
    # arrange
    output = mock.Mock()

    @dataclass
    class BadConfig(BaseConfig):
        _variable_0: int
        variable_1: int
        variable_2: str
        variable_3: bool = False

    # act
    with (
        patch.dict(
            'os.environ',
            BADCONFIG__VARIABLE_1='1',
            BADCONFIG__VARIABLE_2='string',
        ),
        pytest.raises(SystemExit),
    ):
        from_env(BadConfig, output=output)

    # assert
    output.assert_has_calls(
        [
            mock.call(
                "Field '_variable_0' is supposed to have a default value"
            ),
        ]
    )


def test_base_config_skipped():
    """Must create config with skipped env variables."""
    # arrange
    output = mock.Mock()

    @dataclass
    class EasyConfig(BaseConfig):
        variable_1: int
        variable_2: str
        _variable_3: int = 0
        _variable_4: str = 'a'

    # act
    with patch.dict(
        'os.environ',
        EASYCONFIG__VARIABLE_1='1',
        EASYCONFIG__VARIABLE_2='string',
    ):
        config = from_env(EasyConfig, output=output)

    # assert
    assert config.variable_1 == 1
    assert config.variable_2 == 'string'
    assert config._variable_3 == 0
    assert config._variable_4 == 'a'


def test_base_config_medium():
    """Must create config instance from env vars."""

    # arrange
    @dataclass
    class MediumConfig(BaseConfig):
        variable_1: Annotated[int, int]
        variable_2: Annotated[str, str.title]
        variable_3: Annotated[bool, Boolean()]

    # act
    with patch.dict(
        'os.environ',
        MEDIUMCONFIG__VARIABLE_1='1',
        MEDIUMCONFIG__VARIABLE_2='string',
        MEDIUMCONFIG__VARIABLE_3='true',
    ):
        config = from_env(MediumConfig)

    # assert
    assert config.variable_1 == 1
    assert config.variable_2 == 'String'
    assert config.variable_3


def test_base_config_hard():
    """Must create config instance from env vars."""
    # arrange

    @dataclass
    class Database(BaseConfig):
        url: str
        timeout: int

    @dataclass
    class Email(BaseConfig):
        email: str
        retries: bool = False

    @dataclass
    class HardConfig(BaseConfig):
        variable_1: int
        email: Email
        database: Database

    # act
    with patch.dict(
        'os.environ',
        HARDCONFIG__VARIABLE_1='1',
        HARDCONFIG__EMAIL__EMAIL='john@snow.com',
        HARDCONFIG__DATABASE__URL='https://site.com',
        HARDCONFIG__DATABASE__TIMEOUT='1',
    ):
        config = from_env(HardConfig)

    # assert
    assert config.variable_1 == 1
    assert config.email.email == 'john@snow.com'
    assert config.database.url == 'https://site.com'
    assert config.database.timeout == 1


def test_secret_str_len():
    """Must use magic method of the object."""
    # arrange
    reference = 'hello world'

    # act
    target = SecretStr(reference)

    # assert
    assert len(reference) == len(target)


def test_secret_str_test_1():
    """Must use magic method of the object."""
    # arrange
    reference = 'hello world'

    # act
    target = SecretStr(reference)

    # assert
    assert str(target) == repr(target) != reference


def test_secret_str_test_2():
    """Must use magic method of the object."""
    # arrange
    reference = 'hello world'

    # act
    target = SecretStr(reference)

    # assert
    assert set(str(target)) == {'*'}


def test_secret_str_get():
    """Must use magic method of the object."""
    # arrange
    reference = 'hello world'

    # act
    target = SecretStr(reference)

    # assert
    assert target != reference
    assert target.get_secret_value() == reference


def test_base_config_wrong_type():
    """Must fail to create config because wrong type is used."""
    # arrange
    output = mock.Mock()

    @dataclass
    class BadConfig(BaseConfig):
        variable_1: Annotated[str, int]

    # act
    with (
        patch.dict(
            'os.environ',
            BADCONFIG__VARIABLE_1='test',
        ),
        pytest.raises(SystemExit),
    ):
        from_env(BadConfig, output=output)

    # assert
    output.assert_has_calls(
        [
            mock.call(
                "Failed to convert 'variable_1' to type 'str', "
                'got ValueError: invalid literal for'
                " int() with base 10: 'test'"
            ),
        ]
    )


def test_base_config_wrong_logic():
    """Must fail to create config because wrong value is used."""
    # arrange
    output = mock.Mock()

    def bigger_than_one(value: Any) -> Any:
        """Raise if we've got wrong value."""
        if int(value) <= 1:
            msg = 'Not bigger'
            raise ConfigValidationError(msg)

    @dataclass
    class BadConfig(BaseConfig):
        variable_1: Annotated[str, bigger_than_one]

    # act
    with (
        patch.dict(
            'os.environ',
            BADCONFIG__VARIABLE_1='1',
        ),
        pytest.raises(SystemExit),
    ):
        from_env(BadConfig, output=output)

    # assert
    output.assert_has_calls([mock.call('Not bigger')])


def test_base_config_alias_good_1():
    """Must find variable."""
    # arrange

    @dataclass
    class GoodConfig(BaseConfig):
        variable_1: Annotated[str, EnvAlias('MY_OTHER_VARIABLE')]

    # act
    with patch.dict(
        'os.environ',
        MY_OTHER_VARIABLE='1',
    ):
        config = from_env(GoodConfig)

    # assert
    assert config.variable_1 == '1'


def test_base_config_alias_good_2():
    """Must find variable using initial name."""
    # arrange

    @dataclass
    class GoodConfig(BaseConfig):
        variable_1: Annotated[str, EnvAlias('MY_OTHER_VARIABLE')]

    # act
    with patch.dict(
        'os.environ',
        GOODCONFIG__VARIABLE_1='1',
    ):
        config = from_env(GoodConfig)

    # assert
    assert config.variable_1 == '1'


def test_base_config_alias_bad():
    """Must fail to create config because no env variables are set."""
    # arrange
    output = mock.Mock()

    @dataclass
    class BadConfig(BaseConfig):
        variable_1: Annotated[str, EnvAlias('_A', '_B', '_C')]

    # act
    with pytest.raises(SystemExit):
        from_env(BadConfig, output=output)

    # assert
    output.assert_has_calls(
        [
            mock.call(
                'None of expected environment variables are set: '
                "'BADCONFIG__VARIABLE_1', '_A', '_B', '_C'"
            )
        ]
    )


def test_base_config_alias_good_strict():
    """Must find variable using different name."""
    # arrange

    @dataclass
    class GoodConfig(BaseConfig):
        variable_1: Annotated[str, EnvAliasStrict('LAMBDA')]

    # act
    with patch.dict(
        'os.environ',
        LAMBDA='1',
    ):
        config = from_env(GoodConfig)

    # assert
    assert config.variable_1 == '1'


def test_base_config_alias_bad_strict():
    """Must fail to create config because no env variables are set."""
    # arrange
    output = mock.Mock()

    @dataclass
    class BadConfig(BaseConfig):
        variable_1: Annotated[str, EnvAliasStrict('LAMBDA')]

    # act
    with pytest.raises(SystemExit):
        from_env(BadConfig, output=output)

    # assert
    output.assert_has_calls(
        [mock.call("None of expected environment variables are set: 'LAMBDA'")]
    )


@pytest.mark.parametrize(
    ('instance', 'string'),
    [
        (EnvAlias('A', 'B', 'C'), "EnvAlias('A', 'B', 'C')"),
        (EnvAliasStrict('D', 'E', 'F'), "EnvAliasStrict('D', 'E', 'F')"),
    ],
)
def test_alias_repr(instance, string):
    """Must check conversion to a string."""
    # assert
    assert str(instance) == string


def test_base_config_default():
    """Must create config using default."""
    # arrange
    output = mock.Mock()

    @dataclass
    class GoodConfig(BaseConfig):
        variable_1: Annotated[tuple, json.loads] = ('key',)

    # act
    config = from_env(GoodConfig, output=output)

    # assert
    assert config.variable_1 == ('key',)


def test_base_config_long_conversion():
    """Must create config using more than one step of casting."""
    # arrange
    output = mock.Mock()
    reference = 2

    @dataclass
    class GoodConfig(BaseConfig):
        variable_1: Annotated[
            tuple,
            int,
            float,
            lambda x: x['value'],
            lambda x: x['key'],
            json.loads,
        ]

    # act
    with patch.dict(
        'os.environ',
        GOODCONFIG__VARIABLE_1='{"key": {"value": 2.55}}',
    ):
        config = from_env(GoodConfig, output=output)

    # assert
    assert config.variable_1 == reference


def test_nullable():
    """Must create str | None parameter."""
    # arrange
    output = mock.Mock()
    reference = 25

    @dataclass
    class GoodConfig(BaseConfig):
        variable_1: Annotated[int | None, Nullable(int)]
        variable_2: Annotated[int | None, Nullable(int)]

    # act
    with patch.dict(
        'os.environ',
        GOODCONFIG__VARIABLE_1=str(reference),
        GOODCONFIG__VARIABLE_2='null',
    ):
        config = from_env(GoodConfig, output=output)

    # assert
    assert config.variable_1 == reference
    assert config.variable_2 is None


def test_choices_good():
    """Ensure that given variant is included into choices."""
    # arrange
    output = mock.Mock()
    reference = 'two'

    @dataclass
    class GoodConfig(BaseConfig):
        variable: Annotated[str, Choices('one', 'two')]

    # act
    with patch.dict(
        'os.environ',
        GOODCONFIG__VARIABLE=reference,
    ):
        config = from_env(GoodConfig, output=output)

    # assert
    assert config.variable == reference


def test_choices_bad():
    """Ensure that given variant is not included into choices."""
    # arrange
    output = mock.Mock()

    @dataclass
    class BadConfig(BaseConfig):
        variable: Annotated[str, Choices('one', 'two')]

    # act
    with (
        patch.dict(
            'os.environ',
            BADCONFIG__VARIABLE='three',
        ),
        pytest.raises(SystemExit),
    ):
        from_env(BadConfig, output=output)

    # assert
    output.assert_has_calls(
        [
            mock.call(
                'Field BADCONFIG__VARIABLE is expected '
                "to be one of ('one', 'two'), got 'three'"
            )
        ]
    )


def test_interval_good():
    """Ensure that given value is within range (including)."""
    # arrange
    output = mock.Mock()
    reference = 7

    @dataclass
    class GoodConfig(BaseConfig):
        variable: Annotated[str, Interval(0, 15)]

    # act
    with patch.dict(
        'os.environ',
        GOODCONFIG__VARIABLE=str(reference),
    ):
        config = from_env(GoodConfig, output=output)

    # assert
    assert config.variable == reference


def test_interval_too_low():
    """Ensure that given value is out of bounds."""
    # arrange
    output = mock.Mock()

    @dataclass
    class BadConfig(BaseConfig):
        variable: Annotated[str, Interval(0, 15)]

    # act
    with (
        patch.dict(
            'os.environ',
            BADCONFIG__VARIABLE='-16',
        ),
        pytest.raises(SystemExit),
    ):
        from_env(BadConfig, output=output)

    # assert
    output.assert_has_calls(
        [mock.call('BADCONFIG__VARIABLE is smaller than minimum, -16 < 0')]
    )


def test_interval_too_big():
    """Ensure that given value is out of bounds."""
    # arrange
    output = mock.Mock()

    @dataclass
    class BadConfig(BaseConfig):
        variable: Annotated[str, Interval(0.1, 0.2, cast=float)]

    # act
    with (
        patch.dict(
            'os.environ',
            BADCONFIG__VARIABLE='0.45',
        ),
        pytest.raises(SystemExit),
    ):
        from_env(BadConfig, output=output)

    # assert
    output.assert_has_calls(
        [mock.call('BADCONFIG__VARIABLE is bigger than maximum, 0.45 > 0.2')]
    )


def test_interval_wrong_type():
    """Ensure that given value is not integer."""
    # arrange
    output = mock.Mock()

    @dataclass
    class BadConfig(BaseConfig):
        variable: Annotated[str, Interval(0, 15)]

    # act
    with (
        patch.dict(
            'os.environ',
            BADCONFIG__VARIABLE='sixteen',
        ),
        pytest.raises(SystemExit),
    ):
        from_env(BadConfig, output=output)

    # assert
    output.assert_has_calls(
        [mock.call("Failed to convert BADCONFIG__VARIABLE, got 'sixteen'")]
    )


def test_separated():
    """Ensure that is split correctly."""
    # arrange
    output = mock.Mock()
    reference = ['foo', 'bar', 'baz']

    @dataclass
    class GoodConfig(BaseConfig):
        variable: Annotated[list[str], Separated()]

    # act
    with patch.dict(
        'os.environ',
        GOODCONFIG__VARIABLE=' , '.join(reference),
    ):
        config = from_env(GoodConfig, output=output)

    # assert
    assert config.variable == reference


def test_unset_strict():
    """Must fail to create config because no env variables are set."""
    # arrange
    output = mock.Mock()

    @dataclass
    class BadConfig(BaseConfig):
        variable_1: str

    # act
    with pytest.raises(SystemExit):
        from_env(BadConfig, output=output)

    # assert
    output.assert_has_calls(
        [mock.call("Environment variable 'BADCONFIG__VARIABLE_1' is not set")]
    )


def test_unset_annotated():
    """Must fail to create config because no env variables are set."""
    # arrange
    output = mock.Mock()

    @dataclass
    class BadConfig(BaseConfig):
        variable_1: Annotated[str, str]

    # act
    with pytest.raises(SystemExit):
        from_env(BadConfig, output=output)

    # assert
    output.assert_has_calls(
        [mock.call("Environment variable 'BADCONFIG__VARIABLE_1' is not set")]
    )
