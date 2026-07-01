"""FIT file extraction and decoding helpers."""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nono_sports.core.errors import ConfigurationError


@dataclass(frozen=True)
class FitPayload:
    name: str
    payload: bytes


@dataclass(frozen=True)
class FitDecodeResult:
    backend: str
    messages: dict[str, list[dict[str, Any]]]
    frames: int
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class FitDecoderComparison:
    fit_path: str
    fitdecode: dict[str, Any]
    garmin_fit_sdk: dict[str, Any]
    message_types_equal: bool
    sdk_non_null_fields_not_in_fitdecode: dict[str, list[str]]
    fitdecode_non_null_fields_not_in_sdk: dict[str, list[str]]
    sdk_fields_not_in_fitdecode: dict[str, list[str]]
    fitdecode_fields_not_in_sdk: dict[str, list[str]]


def is_fit_payload(payload: bytes) -> bool:
    return len(payload) >= 12 and payload[8:12] == b".FIT"


def extract_fit_payloads(
    payload: bytes,
    *,
    default_name: str = "activity.fit",
) -> list[FitPayload]:
    if is_fit_payload(payload):
        return [FitPayload(name=default_name, payload=payload)]
    if not zipfile.is_zipfile(io.BytesIO(payload)):
        raise ValueError(
            "Payload is neither a FIT file nor a ZIP containing FIT files."
        )

    fit_payloads: list[FitPayload] = []
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for name in archive.namelist():
            if name.lower().endswith(".fit"):
                fit_payloads.append(
                    FitPayload(name=Path(name).name, payload=archive.read(name))
                )
    if not fit_payloads:
        raise ValueError("ZIP payload does not contain FIT files.")
    return fit_payloads


def decode_fit_with_fitdecode(path: Path) -> FitDecodeResult:
    fitdecode = _load_fitdecode()
    messages: dict[str, list[dict[str, Any]]] = {}
    frames = 0
    errors: list[str] = []
    try:
        with fitdecode.FitReader(str(path)) as fit:
            for frame in fit:
                frames += 1
                if frame.frame_type != fitdecode.FIT_FRAME_DATA:
                    continue
                message = _fitdecode_message_to_dict(frame)
                messages.setdefault(str(frame.name), []).append(message)
    except Exception as error:  # noqa: BLE001
        errors.append(str(error))
    return FitDecodeResult(
        backend="fitdecode",
        messages=messages,
        frames=frames,
        errors=tuple(errors),
    )


def compare_fit_decoders(path: Path) -> FitDecoderComparison:
    """Compare the project FIT backend with Garmin's official SDK.

    This is intentionally source-agnostic: the FIT can come from Garmin,
    Komoot, a manual import, or any future provider.
    """

    fitdecode_result = decode_fit_with_fitdecode(path)
    sdk_messages, sdk_errors = _decode_fit_with_garmin_fit_sdk(path)

    fitdecode_fields, fitdecode_non_null = _field_sets_from_messages(
        fitdecode_result.messages
    )
    sdk_fields, sdk_non_null = _field_sets_from_messages(sdk_messages)

    message_types_equal = sorted(fitdecode_fields) == sorted(sdk_fields)
    return FitDecoderComparison(
        fit_path=str(path),
        fitdecode={
            "backend": fitdecode_result.backend,
            "errors": list(fitdecode_result.errors),
            "frames": fitdecode_result.frames,
            "message_counts": _message_counts(fitdecode_result.messages),
        },
        garmin_fit_sdk={
            "backend": "garmin-fit-sdk",
            "errors": sdk_errors,
            "message_counts": _message_counts(sdk_messages),
        },
        message_types_equal=message_types_equal,
        sdk_non_null_fields_not_in_fitdecode=_set_diff(
            sdk_non_null,
            fitdecode_non_null,
        ),
        fitdecode_non_null_fields_not_in_sdk=_set_diff(
            fitdecode_non_null,
            sdk_non_null,
        ),
        sdk_fields_not_in_fitdecode=_set_diff(sdk_fields, fitdecode_fields),
        fitdecode_fields_not_in_sdk=_set_diff(fitdecode_fields, sdk_fields),
    )


def fit_decoder_comparison_to_dict(
    comparison: FitDecoderComparison,
) -> dict[str, Any]:
    return {
        "fit_path": comparison.fit_path,
        "fitdecode": comparison.fitdecode,
        "garmin_fit_sdk": comparison.garmin_fit_sdk,
        "message_types_equal": comparison.message_types_equal,
        "sdk_non_null_fields_not_in_fitdecode": (
            comparison.sdk_non_null_fields_not_in_fitdecode
        ),
        "fitdecode_non_null_fields_not_in_sdk": (
            comparison.fitdecode_non_null_fields_not_in_sdk
        ),
        "sdk_fields_not_in_fitdecode": comparison.sdk_fields_not_in_fitdecode,
        "fitdecode_fields_not_in_sdk": comparison.fitdecode_fields_not_in_sdk,
    }


def write_fit_decode_json(result: FitDecodeResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "backend": result.backend,
        "errors": list(result.errors),
        "frames": result.frames,
        "messages": result.messages,
    }
    path.write_text(
        f"{json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )


def _fitdecode_message_to_dict(frame: Any) -> dict[str, Any]:
    message = {
        "_fit_message": {
            "global_mesg_num": _json_safe_value(
                getattr(frame, "global_mesg_num", None)
            ),
            "local_mesg_num": _json_safe_value(
                getattr(frame, "local_mesg_num", None)
            ),
            "name": _json_safe_value(getattr(frame, "name", None)),
        },
        "_fit_fields": [],
    }
    for field in frame.fields:
        message[field.name] = _json_safe_value(field.value)
        message["_fit_fields"].append(_fitdecode_field_to_dict(field))
    return message


def _fitdecode_field_to_dict(field: Any) -> dict[str, Any]:
    return {
        "name": _json_safe_value(getattr(field, "name", None)),
        "def_num": _json_safe_value(getattr(field, "def_num", None)),
        "value": _json_safe_value(getattr(field, "value", None)),
        "raw_value": _json_safe_value(getattr(field, "raw_value", None)),
        "units": _json_safe_value(getattr(field, "units", None)),
        "type": _fitdecode_type_to_dict(getattr(field, "type", None)),
        "base_type": _fitdecode_type_to_dict(getattr(field, "base_type", None)),
    }


def _fitdecode_type_to_dict(field_type: Any) -> dict[str, Any] | None:
    if field_type is None:
        return None
    return {
        "name": _json_safe_value(getattr(field_type, "name", None)),
        "identifier": _json_safe_value(getattr(field_type, "identifier", None)),
        "type_num": _json_safe_value(getattr(field_type, "type_num", None)),
        "size": _json_safe_value(getattr(field_type, "size", None)),
    }


def _json_safe_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, tuple):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(_json_safe_value(key)): _json_safe_value(item)
            for key, item in value.items()
        }
    return value


def _decode_fit_with_garmin_fit_sdk(path: Path) -> tuple[dict[str, list[dict]], list]:
    garmin_fit_sdk = _load_garmin_fit_sdk()
    decoder = garmin_fit_sdk.Decoder(garmin_fit_sdk.Stream.from_file(str(path)))
    messages, errors = decoder.read()
    return _normalize_garmin_fit_sdk_messages(messages), list(errors)


def _normalize_garmin_fit_sdk_messages(
    messages: dict[str, list[dict]],
) -> dict[str, list[dict[str, Any]]]:
    normalized: dict[str, list[dict[str, Any]]] = {}
    for message_name, rows in messages.items():
        normalized_name = _normalize_sdk_message_name(str(message_name))
        normalized[normalized_name] = [
            {
                _normalize_sdk_field_name(field_name): _json_safe_value(value)
                for field_name, value in row.items()
            }
            for row in rows
        ]
    return normalized


def _normalize_sdk_message_name(message_name: str) -> str:
    if message_name.isdigit():
        return f"unknown_{message_name}"
    if message_name.endswith("_mesgs"):
        return message_name.removesuffix("_mesgs")
    return message_name


def _normalize_sdk_field_name(field_name: Any) -> str:
    if isinstance(field_name, int):
        return f"unknown_{field_name}"
    return str(field_name)


def _field_sets_from_messages(
    messages: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    fields: dict[str, set[str]] = {}
    non_null_fields: dict[str, set[str]] = {}
    for message_name, rows in messages.items():
        fields[message_name] = set()
        non_null_fields[message_name] = set()
        for row in rows:
            for field_name, value in row.items():
                if field_name.startswith("_fit_"):
                    continue
                fields[message_name].add(field_name)
                if _has_non_null_value(value):
                    non_null_fields[message_name].add(field_name)
    return fields, non_null_fields


def _has_non_null_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return any(_has_non_null_value(item) for item in value)
    if isinstance(value, dict):
        return any(_has_non_null_value(item) for item in value.values())
    return True


def _message_counts(messages: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {name: len(rows) for name, rows in sorted(messages.items())}


def _set_diff(
    left: dict[str, set[str]],
    right: dict[str, set[str]],
) -> dict[str, list[str]]:
    diff: dict[str, list[str]] = {}
    for message_name in sorted(set(left) | set(right)):
        values = sorted(left.get(message_name, set()) - right.get(message_name, set()))
        if values:
            diff[message_name] = values
    return diff


def _load_fitdecode() -> Any:
    try:
        import fitdecode
    except ImportError as error:
        raise ConfigurationError(
            "Missing optional FIT dependency. Install it with: "
            "./.venv/bin/python -m pip install -e '.[fit]'"
        ) from error
    return fitdecode


def _load_garmin_fit_sdk() -> Any:
    try:
        import garmin_fit_sdk
    except ImportError as error:
        raise ConfigurationError(
            "Missing optional FIT comparison dependency. Install it with: "
            "./.venv/bin/python -m pip install -e '.[fit-compare]'"
        ) from error
    return garmin_fit_sdk
