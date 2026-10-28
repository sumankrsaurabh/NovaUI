"""Validated small-file uploads over the bounded event bridge."""

from __future__ import annotations

import base64
import binascii
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .components import Component

_ACCEPT_ITEM = re.compile(r"^(?:\.[A-Za-z0-9]{1,16}|[A-Za-z0-9.+-]+/[A-Za-z0-9.+*-]+)$")
_MIME = re.compile(r"^[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+$")


@dataclass(frozen=True)
class UploadedFile:
    """A bounded upload's validated metadata and raw bytes."""

    name: str
    content_type: str
    data: bytes


class _UploadHandler:
    accepts_value = True

    def __init__(
        self,
        owner: FileUpload,
        callback: Callable[[UploadedFile], Any],
        accept: tuple[str, ...],
        max_size: int,
    ):
        self.owner = owner
        self.callback = callback
        self.accept = accept
        self.max_size = max_size

    def __call__(self, value: Mapping[str, str]) -> Any:
        if self.owner.disabled:
            raise ValueError("This file upload control is disabled.")
        if not isinstance(value, Mapping) or set(value) != {"name", "type", "content"}:
            raise ValueError("File upload metadata is invalid.")
        name, content_type, encoded = value["name"], value["type"], value["content"]
        if (not isinstance(name, str) or not name or len(name) > 255
                or any(char in name for char in ("/", "\\", "\x00"))
                or any(ord(char) < 32 or ord(char) == 127 for char in name)):
            raise ValueError("Uploaded filename is invalid.")
        if not isinstance(content_type, str) or (
            content_type and (len(content_type) > 255 or not _MIME.fullmatch(content_type))
        ):
            raise ValueError("Uploaded content type is invalid.")
        if not isinstance(encoded, str) or len(encoded) > 8000:
            raise ValueError("Encoded upload content is invalid or too large.")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Uploaded file content is not valid base64.") from exc
        if len(data) > self.max_size:
            raise ValueError(f"Uploaded file exceeds the {self.max_size}-byte size limit.")
        if self.accept and not any(
            (item.startswith(".") and name.lower().endswith(item.lower()))
            or item == content_type
            or (item.endswith("/*") and content_type.startswith(item[:-1]))
            for item in self.accept
        ):
            raise ValueError("Uploaded file type is not accepted.")
        return self.callback(UploadedFile(name, content_type, data))


class FileUpload(Component):
    """A size-limited upload control for small files submitted to Python callbacks."""

    def __init__(
        self,
        on_upload: Callable[[UploadedFile], Any],
        *,
        label: str = "Choose a file",
        accept: str = "",
        max_size: int = 5000,
        disabled: bool = False,
        **props: Any,
    ):
        super().__init__(**props)
        self.on_upload = on_upload
        self.label = label
        self.accept = accept
        self.max_size = max_size
        self.disabled = disabled

    def to_dict(self, register_event):
        if not callable(self.on_upload):
            raise TypeError("FileUpload on_upload must be callable.")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("FileUpload label must be a non-empty string.")
        if not isinstance(self.accept, str):
            raise TypeError("FileUpload accept must be a comma-separated string.")
        accepted = tuple(item.strip() for item in self.accept.split(",") if item.strip())
        if any(not _ACCEPT_ITEM.fullmatch(item) for item in accepted):
            raise ValueError("FileUpload accept contains an unsupported file extension or MIME type.")
        if (isinstance(self.max_size, bool) or not isinstance(self.max_size, int)
                or not 1 <= self.max_size <= 6000):
            raise ValueError("FileUpload max_size must be an integer from 1 to 6000 bytes.")
        if not isinstance(self.disabled, bool):
            raise TypeError("FileUpload disabled must be a bool.")
        return {
            "id": self._node_id(),
            "type": "file_upload",
            "label": self.label,
            "accept": self.accept,
            "max_size": self.max_size,
            "disabled": self.disabled,
            "event_id": (
                register_event(_UploadHandler(self, self.on_upload, accepted, self.max_size))
                if not self.disabled else None
            ),
            **self._common_props(),
        }
