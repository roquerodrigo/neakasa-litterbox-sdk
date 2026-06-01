"""Parse fixture payloads from the Neakasa REST endpoints."""

from __future__ import annotations

from neakasa_litterbox_sdk import (
    Cat,
    CatGender,
    DailyStatistics,
    DeviceStatus,
    OperatingState,
    RecordType,
    ToiletRecord,
)


def test_cat_parses_live_sample() -> None:
    """Real ``catbox/cat/list`` entry from the test account."""
    raw = {
        "id": 113196,
        "name": "Mini",
        "weight": 3,
        "unit": "kg",
        "avatar": "https://jhc-en.oss-ap-southeast-1.aliyuncs.com/user/.../mini.png",
        "birthday": "",
        "variety": -1,
        "gender": 2,
        "sterilization": 1,
        "enabled": 1,
        "path": "user/400068852/catbox/PB01009G25110010081/1750883181.png",
    }
    cat = Cat.from_json(raw)
    assert cat.id == 113196
    assert cat.name == "Mini"
    assert cat.weight == 3.0
    assert cat.gender is CatGender.FEMALE
    assert cat.is_sterilized
    assert cat.is_enabled


def test_cat_unknown_gender_falls_back() -> None:
    cat = Cat.from_json({"id": 1, "name": "?", "gender": 99})
    assert cat.gender is CatGender.UNKNOWN


def test_cat_list_from_response_filters_non_objects() -> None:
    cats = Cat.list_from_response(
        [
            {"id": 1, "name": "A", "weight": 1.0, "gender": 1},
            "not an object",
            {"id": 2, "name": "B", "weight": 2.0, "gender": 2},
        ]
    )
    assert [c.id for c in cats] == [1, 2]


def test_cat_list_from_response_handles_unexpected_top_level() -> None:
    assert Cat.list_from_response({"unexpected": "object"}) == []
    assert Cat.list_from_response(None) == []
    assert Cat.list_from_response("string") == []


def test_toilet_record_visit_sample() -> None:
    """``type=1`` row from a cat visiting the box."""
    raw = {
        "type": 1,
        "record_id": 182739595,
        "cat_id": 113196,
        "start_time": 1779189528,
        "end_time": 1779189563,
        "weight": 2.9,
        "unit": "kg",
        "way": 0,
    }
    record = ToiletRecord.from_json(raw)
    assert record.record_type is RecordType.CAT_VISIT
    assert record.cat_id == 113196
    assert record.weight == 2.9
    assert record.duration_seconds == 35


def test_toilet_record_clean_cycle_sample() -> None:
    """``type=2`` row from an auto-clean cycle."""
    raw = {
        "type": 2,
        "record_id": 141548746,
        "cat_id": 0,
        "start_time": 1779189865,
        "end_time": 1779190006,
        "weight": 20,
        "unit": "",
        "way": 1,
    }
    record = ToiletRecord.from_json(raw)
    assert record.record_type is RecordType.CLEAN_CYCLE
    assert record.cat_id == 0
    assert record.unit == ""


def test_toilet_record_list_from_response_unwraps_envelope() -> None:
    payload = {
        "record_list": [
            {"type": 1, "record_id": 1, "cat_id": 0, "start_time": 0, "end_time": 1},
            {"type": 2, "record_id": 2, "cat_id": 0, "start_time": 2, "end_time": 3},
        ]
    }
    records = ToiletRecord.list_from_response(payload)
    assert [r.record_id for r in records] == [1, 2]
    assert records[0].record_type is RecordType.CAT_VISIT
    assert records[1].record_type is RecordType.CLEAN_CYCLE


def test_toilet_record_list_from_response_tolerates_missing_envelope() -> None:
    assert ToiletRecord.list_from_response({}) == []
    assert ToiletRecord.list_from_response(None) == []
    assert ToiletRecord.list_from_response([{"type": 1}]) == []  # not the wrapped shape


def _wrap(value: object) -> dict[str, object]:
    """Wrap a value in the ``{"time", "value"}`` envelope the cloud uses."""
    return {"time": 1, "value": value}


def test_device_status_bucket_full_reads_room_of_bin() -> None:
    """``room_of_bin`` drives ``bucket_full`` (1 = full); ``bucketStatus`` is ignored."""
    full = DeviceStatus.from_response({"room_of_bin": _wrap(1), "bucketStatus": _wrap(0)})
    empty = DeviceStatus.from_response({"room_of_bin": _wrap(0), "bucketStatus": _wrap(1)})
    assert full.bucket_full is True
    assert empty.bucket_full is False


def test_device_status_operating_state_reads_bucket_status() -> None:
    """``bucketStatus`` is the activity code, mapped to ``operating_state``."""
    assert (
        DeviceStatus.from_response({"bucketStatus": _wrap(2)}).operating_state
        is OperatingState.CLEANING
    )
    assert (
        DeviceStatus.from_response({"bucketStatus": _wrap(0)}).operating_state
        is OperatingState.IDLE
    )
    # Absent property → defaults to idle (0); unknown code → UNKNOWN.
    assert DeviceStatus.from_response({}).operating_state is OperatingState.IDLE
    assert (
        DeviceStatus.from_response({"bucketStatus": _wrap(99)}).operating_state
        is OperatingState.UNKNOWN
    )


def test_operating_state_from_code() -> None:
    assert OperatingState.from_code(3) is OperatingState.LEVELING
    assert OperatingState.from_code(1) is OperatingState.RESTORING
    assert OperatingState.from_code(5) is OperatingState.CAT_APPEARS
    assert OperatingState.from_code(7) is OperatingState.UNKNOWN


def test_operating_state_unmapped_code_warns_once(caplog) -> None:
    import logging

    from neakasa_litterbox_sdk.models import operating_state as os_mod

    os_mod._warned_codes.discard(42)
    with caplog.at_level(logging.WARNING, logger=os_mod.__name__):
        assert OperatingState.from_code(42) is OperatingState.UNKNOWN
        assert OperatingState.from_code(42) is OperatingState.UNKNOWN  # deduped
    warnings = [r for r in caplog.records if "42" in r.getMessage()]
    assert len(warnings) == 1


def test_daily_statistics_parses_live_sample() -> None:
    raw = {
        "date": "2026-04-23",
        "num": 11,
        "weight": 4.8,
        "unit": "kg",
        "toilet_total_second": 760,
        "weight_avg": 3.67,
    }
    stats = DailyStatistics.from_json(raw)
    assert stats.date == "2026-04-23"
    assert stats.num == 11
    assert stats.toilet_total_second == 760
    assert stats.weight_avg == 3.67


def test_daily_statistics_list_from_response() -> None:
    stats = DailyStatistics.list_from_response(
        [
            {"date": "2026-04-23", "num": 11, "toilet_total_second": 760},
            {"date": "2026-04-24", "num": 9, "toilet_total_second": 694},
        ]
    )
    assert [s.date for s in stats] == ["2026-04-23", "2026-04-24"]
    assert DailyStatistics.list_from_response(None) == []
