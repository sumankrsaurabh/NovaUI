"""Python-side form fields, validation, and submission lifecycle."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from .components import Component, Input
from .state import State, state

_logger = logging.getLogger(__name__)
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_FIELD_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")


class Field:
    """A string form value with reusable Python validation rules."""

    def __init__(
        self,
        value: str = "",
        *,
        label: str | None = None,
        input_type: str = "text",
        placeholder: str = "",
        required: bool = False,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: float | str | None = None,
        max_value: float | str | None = None,
        validator: Callable[[str], str | None] | None = None,
        disabled: bool = False,
    ):
        if not isinstance(value, str):
            raise TypeError("Field value must be a string.")
        if input_type not in {"text", "email", "password", "number", "date"}:
            raise ValueError("Field input_type must be text, email, password, number, or date.")
        if label is not None and not isinstance(label, str):
            raise TypeError("Field label must be a string or None.")
        if not isinstance(placeholder, str):
            raise TypeError("Field placeholder must be a string.")
        if not isinstance(required, bool) or not isinstance(disabled, bool):
            raise TypeError("Field required and disabled values must be bools.")
        for name, length in (("min_length", min_length), ("max_length", max_length)):
            if length is not None and (isinstance(length, bool) or not isinstance(length, int) or length < 0):
                raise ValueError(f"Field {name} must be a non-negative integer or None.")
        if min_length is not None and max_length is not None and min_length > max_length:
            raise ValueError("Field min_length cannot exceed max_length.")
        if validator is not None and not callable(validator):
            raise TypeError("Field validator must be callable or None.")
        for name, bound in (("min_value", min_value), ("max_value", max_value)):
            if bound is not None and (isinstance(bound, bool) or not isinstance(bound, (str, int, float))):
                raise TypeError(f"Field {name} must be a number, numeric string, or None.")
        if input_type == "number":
            try:
                if min_value is not None and max_value is not None and Decimal(str(min_value)) > Decimal(str(max_value)):
                    raise ValueError("Field min_value cannot exceed max_value.")
                for bound in (min_value, max_value):
                    if bound is not None and not Decimal(str(bound)).is_finite():
                        raise ValueError("Field numeric bounds must be finite.")
            except InvalidOperation as exc:
                raise ValueError("Field numeric bounds must be valid numbers.") from exc
        elif min_value is not None or max_value is not None:
            raise ValueError("Field min_value and max_value require input_type='number'.")

        self.label = label
        self.input_type = input_type
        self.placeholder = placeholder
        self.required = required
        self.min_length = min_length
        self.max_length = max_length
        self.min_value = min_value
        self.max_value = max_value
        self.validator = validator
        self.disabled = disabled
        self._initial_value = value
        self._state: State[str] = state(value)
        self.error: str | None = None
        self.dirty = False

    @property
    def value(self) -> str:
        return self._state.value

    @value.setter
    def value(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Field value must be a string.")
        self._state.update(value)
        self.dirty = value != self._initial_value

    def validate(self, value: str | None = None) -> str | None:
        candidate = self.value if value is None else value
        if not isinstance(candidate, str):
            raise TypeError("Field values must be strings.")
        if self.required and not candidate.strip():
            return "This field is required."
        if candidate and self.min_length is not None and len(candidate) < self.min_length:
            return f"Use at least {self.min_length} characters."
        if self.max_length is not None and len(candidate) > self.max_length:
            return f"Use no more than {self.max_length} characters."
        if self.input_type == "email" and candidate and not _EMAIL.fullmatch(candidate):
            return "Enter a valid email address."
        if self.input_type == "date" and candidate:
            try:
                date.fromisoformat(candidate)
            except ValueError:
                return "Enter a valid date."
        if self.input_type == "number" and candidate:
            try:
                number = Decimal(candidate)
            except InvalidOperation:
                return "Enter a valid number."
            if not number.is_finite():
                return "Enter a valid number."
            if self.min_value is not None and number < Decimal(str(self.min_value)):
                return f"Enter a value of at least {self.min_value}."
            if self.max_value is not None and number > Decimal(str(self.max_value)):
                return f"Enter a value no greater than {self.max_value}."
        if self.validator is not None:
            try:
                error = self.validator(candidate)
            except Exception as exc:  # noqa: BLE001 - validators must not leak exception details to users.
                _logger.error("NovaUI field validator failed with %s", type(exc).__name__)
                return "Could not validate this field."
            if error is not None and not isinstance(error, str):
                raise TypeError("Field validator must return an error string or None.")
            return error
        return None

    def reset(self) -> None:
        self._state.update(self._initial_value)
        self.error = None
        self.dirty = False

    def _on_change(self, value: str) -> str | None:
        self.dirty = value != self._initial_value
        self.error = self.validate(value)
        return self.error


class _SubmitBinding:
    accepts_value = True

    def __init__(self, form: Form):
        self.form = form

    def __call__(self, values: dict[str, str]) -> None:
        self.form.submit(values)


class Form(Component):
    """A component that owns string fields, validation, reset, and submission."""

    def __init__(
        self,
        *,
        fields: Mapping[str, Field],
        on_submit: Callable[[dict[str, str]], Any],
        submit_label: str = "Submit",
        reset_label: str | None = "Reset",
        disabled: bool = False,
        loading: bool = False,
        **props: Any,
    ):
        super().__init__(**props)
        if not isinstance(fields, Mapping) or not fields:
            raise ValueError("Form fields must be a non-empty mapping of names to Field instances.")
        if not callable(on_submit):
            raise TypeError("Form on_submit must be callable.")
        if not isinstance(submit_label, str) or not submit_label:
            raise ValueError("Form submit_label must be a non-empty string.")
        if reset_label is not None and (not isinstance(reset_label, str) or not reset_label):
            raise ValueError("Form reset_label must be a non-empty string or None.")
        if not isinstance(disabled, bool) or not isinstance(loading, bool):
            raise TypeError("Form disabled and loading values must be bools.")
        self.fields = dict(fields)
        for name, field in self.fields.items():
            if not isinstance(name, str) or not _FIELD_NAME.fullmatch(name):
                raise ValueError(f"Invalid form field name: {name!r}.")
            if not isinstance(field, Field):
                raise TypeError(f"Form field {name!r} must be a Field instance.")
        self.on_submit = on_submit
        self.submit_label = submit_label
        self.reset_label = reset_label
        self.disabled = disabled
        self.loading = loading
        self.is_submitting = False
        self.status = ""
        self._inputs = {
            name: Input(
                label=field.label or name.replace("_", " ").title(),
                name=name,
                placeholder=field.placeholder,
                value=field._state,
                input_type=field.input_type,
                required=field.required,
                min_length=field.min_length,
                max_length=field.max_length,
                min_value=field.min_value,
                max_value=field.max_value,
                disabled=field.disabled,
                on_change=field._on_change,
            )
            for name, field in self.fields.items()
        }

    def iter_children(self) -> tuple[Component, ...]:
        return tuple(self._inputs.values())

    def dispose(self) -> None:
        for field in self.fields.values():
            field._state.dispose()

    @property
    def values(self) -> dict[str, str]:
        return {name: field.value for name, field in self.fields.items()}

    @property
    def errors(self) -> dict[str, str]:
        return {name: field.error for name, field in self.fields.items() if field.error is not None}

    @property
    def dirty_fields(self) -> set[str]:
        return {name for name, field in self.fields.items() if field.dirty}

    def revalidate(self) -> bool:
        valid = True
        for name, field in self.fields.items():
            field.error = None if field.disabled else field.validate()
            self._inputs[name].error = field.error
            valid = valid and field.error is None
        return valid

    def reset(self) -> None:
        for name, field in self.fields.items():
            field.reset()
            self._inputs[name].error = None
        self.status = ""
        self.is_submitting = False

    def submit(self, values: dict[str, str]) -> None:
        if self.disabled or self.loading or self.is_submitting:
            return
        if not isinstance(values, dict) or any(
            not isinstance(name, str) or name not in self.fields or not isinstance(value, str)
            for name, value in values.items()
        ):
            raise ValueError("Form submission contains invalid field values.")
        for name, value in values.items():
            self.fields[name].value = value
        if not self.revalidate():
            self.status = "Please fix the highlighted fields."
            return
        self.is_submitting = True
        self.status = ""
        try:
            result = self.on_submit(self.values)
            if result is not None and not isinstance(result, str):
                raise TypeError("Form on_submit must return a string status message or None.")
            self.status = result or "Submitted successfully."
        except Exception as exc:  # noqa: BLE001 - convert callback errors into safe form status.
            _logger.error("NovaUI form submission failed with %s", type(exc).__name__)
            self.status = "Submission failed. Please try again."
        finally:
            self.is_submitting = False

    def to_dict(self, register_event):
        if not isinstance(self.disabled, bool) or not isinstance(self.loading, bool):
            raise TypeError("Form disabled and loading values must be bools.")
        for name, field in self.fields.items():
            input_field = self._inputs[name]
            input_field.disabled = self.disabled or self.loading or self.is_submitting or field.disabled
            input_field.error = field.error
        return {
            "id": self._node_id(),
            "type": "form",
            "children": [field.to_dict(register_event) for field in self._inputs.values()],
            "submit_event_id": register_event(_SubmitBinding(self)),
            "reset_event_id": register_event(self.reset) if self.reset_label is not None else None,
            "submit_label": self.submit_label,
            "reset_label": self.reset_label,
            "disabled": self.disabled,
            "loading": self.loading or self.is_submitting,
            "status": self.status,
            **self._common_props(),
        }
