"""Simple config class, when you do not need full size pydantic."""

from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import MISSING
from dataclasses import Field
from dataclasses import dataclass
from dataclasses import fields
import os
import sys
from typing import Annotated
from typing import Any
from typing import TypeVar
from typing import get_args
from typing import get_origin

__all__ = [
    'BaseAlias',
    'BaseConfig',
    'Boolean',
    'Choices',
    'ConfigValidationError',
    'EnvAlias',
    'EnvAliasStrict',
    'Interval',
    'Nullable',
    'SecretStr',
    'from_env',
]


@dataclass
class BaseConfig:
    """Configuration base class."""


class ConfigValidationError(Exception):
    """Failed to cast attribute to expected type."""


class SecretStr:
    """String that does not show its value."""

    def __init__(self, secret_value: str) -> None:
        """Initialize instance."""
        self._secret_value = secret_value

    def get_secret_value(self) -> str:
        """Return secret value."""
        return self._secret_value

    def __len__(self) -> int:
        """Return number of symbols."""
        return len(self._secret_value)

    def __str__(self) -> str:
        """Return string representation."""
        return '**********' if self.get_secret_value() else ''

    def __repr__(self) -> str:
        """Return string representation."""
        return self.__str__()


class BaseAlias:
    """Base class for aliases."""

    strict: bool = False

    def __init__(self, *names: str) -> None:
        """Initialize instance."""
        self.names = names

    def __call__(self, value: str | None) -> str | None:
        """Do nothing, juts return."""
        return value

    def __repr__(self) -> str:
        """Return textual representation."""
        name = type(self).__name__
        strings = ', '.join(repr(x) for x in self.names)
        return f'{name}({strings})'

    def find_matching(
        self,
        env_name: str,
    ) -> tuple[str, None] | tuple[None, str]:
        """Try getting value via another name."""
        tried: list[str] = []

        if not self.strict:
            value = os.environ.get(env_name)
            tried.append(repr(env_name))

            if value is not None:
                return value, None

        for name in self.names:
            value = os.environ.get(name)
            tried.append(repr(name))

            if value is not None:
                return value, None

        variables = ', '.join(tried)
        return (
            None,
            f'None of expected environment variables are set: {variables}',
        )


class EnvAlias(BaseAlias):
    """Alternative name or names of environment variable for a field.

    Alias is expected to be the rightmost element in Annotated hint.
    """

    strict = False


class EnvAliasStrict(BaseAlias):
    """Alternative name or names of environment variable for a field.

    Same as EnvAlias, but ignores default variable name and starts
    checking from given aliases.
    """

    strict = True


class Boolean:
    """Return True if value looks like boolean."""

    @staticmethod
    def __call__(value: str) -> Any:
        """Return None if value is null."""
        return value.lower() == 'true'


class Nullable:
    """Return None if value is null."""

    def __init__(self, cast: Callable) -> None:
        """Initialize instance."""
        self.cast = cast

    def __call__(self, value: str) -> Any:
        """Return None if value is null."""
        return None if value.lower() == 'null' else self.cast(value)


class Choices:
    """Ensure that given variant is included into valid choices."""

    def __init__(self, *choices: str, cast: Callable = lambda x: x) -> None:
        """Initialize instance."""
        self.choices = choices
        self.cast = cast

    def __call__(self, value: str) -> Any:
        """Ensure that given variant is included into valid choices."""
        if value not in self.choices:
            msg = (
                f'Field {{env_name}} is expected to '
                f'be one of {self.choices!r}, got {value!r}'
            )
            raise ConfigValidationError(msg)

        return self.cast(value)


class Interval:
    """Ensure that given value is within range."""

    def __init__(
        self, minimum: float, maximum: float, cast: Callable = int
    ) -> None:
        """Initialize instance."""
        self.minimum = minimum
        self.maximum = maximum
        self.cast = cast

    def __call__(self, value: str) -> int:
        """Ensure that given variant is included into valid choices."""
        try:
            number = self.cast(value)
        except (TypeError, ValueError):
            msg = f'Failed to convert {{env_name}}, got {value!r}'
            raise ConfigValidationError(msg) from None

        if self.minimum < number < self.maximum:
            return number

        if number > self.maximum:
            msg = (
                f'{{env_name}} is bigger than maximum, '
                f'{number} > {self.maximum}'
            )
            raise ConfigValidationError(msg)

        msg = (
            f'{{env_name}} is smaller than minimum, {number} < {self.minimum}'
        )
        raise ConfigValidationError(msg)


def _is_excluded(field: Field, field_exclude_prefix: str) -> bool:
    """Return true if this field is excluded from env vars."""
    return bool(
        field_exclude_prefix and field.name.startswith(field_exclude_prefix)
    )


def _has_no_default(field: Field) -> str | None:
    """Return error message if field expects a value."""
    if field.default is MISSING:
        return f'Field {field.name!r} is supposed to have a default value'
    return None


def _try_casting(
    field: Field,
    value: Any,
    env_name: str,
    expected_type: type,
    converter: Callable,
    errors: list[str],
) -> Any:
    """Try to convert type of the input."""
    try:
        final_value = converter(value)
    except ConfigValidationError as exc:
        errors.append(str(exc).format(env_name=env_name, field=field))
        return MISSING
    except Exception as exc:
        msg = (
            f'Failed to convert {field.name!r} '
            f'to type {expected_type.__name__!r}, '
            f'got {type(exc).__name__}: {exc}'
        )
        errors.append(msg)
        return MISSING

    return final_value


T_co = TypeVar('T_co', bound=BaseConfig, covariant=True)


def from_env(
    model_type: type[T_co],
    *,
    env_prefix: str = '',
    env_separator: str = '__',
    field_exclude_prefix: str = '_',
    output: Callable = print,
    _prefixes: list[str] | None = None,
    _terminate: Callable = lambda: sys.exit(1),
) -> T_co:
    """Build instance from environment variables."""
    errors: list[str] = []
    attributes: dict[str, Any] = {}

    if _prefixes is None:
        env_prefix = env_prefix or model_type.__name__.upper()
        _prefixes = _prefixes or [env_prefix, env_separator]

    for field in fields(model_type):
        if _is_excluded(field, field_exclude_prefix):
            msg = _has_no_default(field)
            if msg:
                errors.append(msg)
            continue

        if get_origin(field.type) is Annotated:
            _extract_annotated(field, _prefixes, attributes, errors)
        elif isinstance(field.type, type) and issubclass(
            field.type, BaseConfig
        ):
            _extract_nested(
                field=field,
                field_exclude_prefix=field_exclude_prefix,
                env_separator=env_separator,
                prefixes=_prefixes,
                attributes=attributes,
                output=output,
                terminate=_terminate,
            )
        else:
            _extract_straightforward(field, _prefixes, attributes, errors)

    if errors:
        for error in errors:
            output(error)
        _terminate()

    return model_type(**attributes)


def _extract_straightforward(
    field: Field,
    prefixes: list[str],
    attributes: dict[str, Any],
    errors: list[str],
) -> None:
    """Extract value using type itself."""
    prefix = ''.join(prefixes)
    env_name = f'{prefix}{field.name}'.upper()
    value = os.environ.get(env_name)

    if value is not None:
        attributes[field.name] = _try_casting(
            field=field,
            value=value,
            env_name=env_name,
            expected_type=field.type,  # type: ignore [arg-type]
            converter=field.type,  # type: ignore [arg-type]
            errors=errors,
        )
    elif value is None and field.default is not MISSING:
        # using default without data casting
        attributes[field.name] = field.default
    else:
        msg = f'Environment variable {env_name!r} is not set'
        errors.append(msg)


def _extract_annotated(
    field: Field,
    prefixes: Sequence[str],
    attributes: dict[str, Any],
    errors: list[str],
) -> None:
    """Extract value using sequence of casting callables."""
    prefix = ''.join(prefixes)
    env_name = f'{prefix}{field.name}'.upper()

    expected_type, *casting_callables = get_args(field.type)

    if isinstance(casting_callables[-1], BaseAlias):
        value, msg = casting_callables[-1].find_matching(env_name)

        if msg:
            errors.append(msg)
            return

    else:
        value = os.environ.get(env_name)
        if value is None:
            if field.default is not MISSING:
                # using default without data casting
                attributes[field.name] = field.default
                return
            else:
                msg = f'Environment variable {env_name!r} is not set'
                errors.append(msg)
                return

    final_value = value
    for _callable in reversed(casting_callables):
        final_value = _try_casting(
            field=field,
            value=final_value,
            env_name=env_name,
            expected_type=expected_type,
            converter=_callable,
            errors=errors,
        )

        if final_value is MISSING:
            return

    attributes[field.name] = final_value


def _extract_nested(  # noqa: PLR0913
    field: Field,
    field_exclude_prefix: str,
    env_separator: str,
    prefixes: Sequence[str],
    attributes: dict[str, Any],
    output: Callable,
    terminate: Callable,
) -> None:
    """Extract value recursively."""
    value = from_env(
        model_type=field.type,  # type: ignore [arg-type]
        env_prefix='',
        field_exclude_prefix=field_exclude_prefix,
        output=output,
        _prefixes=[*prefixes, field.name.upper(), env_separator],
        _terminate=terminate,
    )
    attributes[field.name] = value
