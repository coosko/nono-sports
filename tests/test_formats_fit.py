import io
import zipfile

from nono_sports.formats.fit import (
    _fitdecode_message_to_dict,
    _normalize_garmin_fit_sdk_messages,
    compare_fit_decoders,
    extract_fit_payloads,
    fit_decoder_comparison_to_dict,
    is_fit_payload,
)

FIT_BYTES = b"\x0e\x20\x00\x00\x00\x00\x00\x00.FIT\x00\x00"


def test_is_fit_payload_detects_fit_header() -> None:
    assert is_fit_payload(FIT_BYTES) is True
    assert is_fit_payload(b"not-fit") is False


def test_extract_fit_payloads_accepts_direct_fit() -> None:
    payloads = extract_fit_payloads(FIT_BYTES, default_name="sample.fit")

    assert len(payloads) == 1
    assert payloads[0].name == "sample.fit"
    assert payloads[0].payload == FIT_BYTES


def test_extract_fit_payloads_extracts_fit_from_zip() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("activity.fit", FIT_BYTES)
        archive.writestr("notes.txt", "ignored")

    payloads = extract_fit_payloads(buffer.getvalue())

    assert len(payloads) == 1
    assert payloads[0].name == "activity.fit"
    assert payloads[0].payload == FIT_BYTES


def test_fitdecode_message_keeps_decoded_values_and_field_metadata() -> None:
    field_type = FakeFitType(
        name="manufacturer",
        identifier="uint16",
        type_num=132,
        size=2,
    )
    field = FakeFitField(
        name="garmin_product",
        def_num=4,
        value="edge_820",
        raw_value=2530,
        units=None,
        field_type=field_type,
        base_type=field_type,
    )
    frame = FakeFitFrame(
        name="device_info",
        global_mesg_num=23,
        local_mesg_num=0,
        fields=[field],
    )

    message = _fitdecode_message_to_dict(frame)

    assert message["garmin_product"] == "edge_820"
    assert message["_fit_message"] == {
        "global_mesg_num": 23,
        "local_mesg_num": 0,
        "name": "device_info",
    }
    assert message["_fit_fields"] == [
        {
            "name": "garmin_product",
            "def_num": 4,
            "value": "edge_820",
            "raw_value": 2530,
            "units": None,
            "type": {
                "name": "manufacturer",
                "identifier": "uint16",
                "type_num": 132,
                "size": 2,
            },
            "base_type": {
                "name": "manufacturer",
                "identifier": "uint16",
                "type_num": 132,
                "size": 2,
            },
        }
    ]


def test_normalize_garmin_fit_sdk_messages_aligns_names() -> None:
    messages = {
        "record_mesgs": [{"timestamp": "now", 61: 5245}],
        "104": [{253: 1151693105}],
    }

    normalized = _normalize_garmin_fit_sdk_messages(messages)

    assert normalized == {
        "record": [{"timestamp": "now", "unknown_61": 5245}],
        "unknown_104": [{"unknown_253": 1151693105}],
    }


def test_compare_fit_decoders_reports_field_differences(monkeypatch, tmp_path) -> None:
    fit_path = tmp_path / "activity.fit"
    fit_path.write_bytes(FIT_BYTES)

    monkeypatch.setattr(
        "nono_sports.formats.fit.decode_fit_with_fitdecode",
        lambda path: FakeFitDecodeResult(
            backend="fitdecode",
            frames=12,
            errors=(),
            messages={"record": [{"speed": 7.0, "_fit_fields": []}]},
        ),
    )
    monkeypatch.setattr(
        "nono_sports.formats.fit._decode_fit_with_garmin_fit_sdk",
        lambda path: (
            {"record": [{"speed": 7.0, "unknown_61": 5245}]},
            [],
        ),
    )

    comparison = compare_fit_decoders(fit_path)

    assert comparison.message_types_equal is True
    assert comparison.sdk_non_null_fields_not_in_fitdecode == {
        "record": ["unknown_61"]
    }
    assert fit_decoder_comparison_to_dict(comparison)["fit_path"] == str(fit_path)


class FakeFitType:
    def __init__(self, name, identifier, type_num, size):
        self.name = name
        self.identifier = identifier
        self.type_num = type_num
        self.size = size


class FakeFitField:
    def __init__(
        self,
        *,
        name,
        def_num,
        value,
        raw_value,
        units,
        field_type,
        base_type,
    ):
        self.name = name
        self.def_num = def_num
        self.value = value
        self.raw_value = raw_value
        self.units = units
        self.type = field_type
        self.base_type = base_type


class FakeFitFrame:
    def __init__(self, *, name, global_mesg_num, local_mesg_num, fields):
        self.name = name
        self.global_mesg_num = global_mesg_num
        self.local_mesg_num = local_mesg_num
        self.fields = fields


class FakeFitDecodeResult:
    def __init__(self, *, backend, messages, frames, errors):
        self.backend = backend
        self.messages = messages
        self.frames = frames
        self.errors = errors
