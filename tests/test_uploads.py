import base64

import pytest

import novaui as ui


def serialize(component):
    events = {}

    def register(callback):
        event_id = f"event-{len(events) + 1}"
        events[event_id] = callback
        return event_id

    return component.to_dict(register), events


def test_file_upload_validates_and_delivers_small_file():
    uploaded = []
    control = ui.FileUpload(uploaded.append, accept=".txt,text/plain", max_size=32)
    tree, events = serialize(control)
    events[tree["event_id"]]({
        "name": "notes.txt",
        "type": "text/plain",
        "content": base64.b64encode(b"hello").decode("ascii"),
    })
    assert uploaded == [ui.UploadedFile("notes.txt", "text/plain", b"hello")]


def test_disabled_upload_does_not_register_callback():
    tree, _ = serialize(ui.FileUpload(lambda file: None, disabled=True))
    assert tree["event_id"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "../notes.txt", "type": "text/plain", "content": "aGVsbG8="},
        {"name": "notes.txt", "type": "text/plain", "content": "%%"},
        {"name": "notes.txt", "type": "text/plain", "content": base64.b64encode(b"too long").decode()},
        {"name": "image.png", "type": "image/png", "content": "aGVsbG8="},
    ],
)
def test_file_upload_rejects_unsafe_or_invalid_payloads(payload):
    tree, events = serialize(ui.FileUpload(lambda file: None, accept=".txt", max_size=5))
    with pytest.raises(ValueError):
        events[tree["event_id"]](payload)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_size": 0},
        {"max_size": 6001},
        {"accept": "bad value"},
        {"disabled": 1},
    ],
)
def test_file_upload_validates_public_options(kwargs):
    with pytest.raises((TypeError, ValueError)):
        serialize(ui.FileUpload(lambda file: None, **kwargs))
