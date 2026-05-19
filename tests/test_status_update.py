"""Property-push parsing — known mappings + raw passthrough."""

from __future__ import annotations

from neakasa_litterbox_sdk.models.status_update import StatusUpdate


def test_known_property_mapping_is_snake_case() -> None:
    """The handful of properties we know about land under DeviceStatus-style keys."""
    update = StatusUpdate.from_push(
        {
            "params": {
                "deviceName": "PB01",
                "items": {
                    "silentMode": {"time": 1, "value": 1},
                    "childLockOnOff": {"time": 1, "value": 0},
                    "Sand": {"time": 1, "value": {"percent": 87, "level": 2, "sand": 1234}},
                    "catLeft": {
                        "time": 1,
                        "value": {"kitten": 1, "stayTime": 42, "needClean": 1},
                    },
                    "cleanCfg": {
                        "time": 1,
                        "value": {"cleanType": 1, "cleanParam": 5, "active": 1},
                    },
                },
            }
        }
    )
    assert update is not None
    assert update.device_name == "PB01"
    assert update.changes == {
        "silent_mode": True,
        "child_lock": False,
        "sand_percent": 87,
        "cat_present": True,
        "cat_stay_seconds": 42,
        "needs_cleaning": True,
        "cleaning_enabled": True,
    }


def test_unknown_property_passes_through_under_camelcase() -> None:
    """A property the SDK doesn't recognise still reaches the consumer raw."""
    update = StatusUpdate.from_push(
        {
            "params": {
                "deviceName": "PB01",
                "items": {
                    "silentMode": {"time": 1, "value": 1},
                    "futureProp": {"time": 1, "value": 99},
                    "Reboot": {"time": 1, "value": {"reason": 1, "rebootTS": "..."}},
                },
            }
        }
    )
    assert update is not None
    assert update.changes["silent_mode"] is True
    assert update.changes["futureProp"] == 99
    assert update.changes["Reboot"] == {"reason": 1, "rebootTS": "..."}


def test_missing_device_or_items_drops_to_none() -> None:
    """Without ``deviceName`` or ``items`` there's nothing actionable."""
    assert StatusUpdate.from_push({"params": {"items": {"silentMode": {"value": 1}}}}) is None
    assert StatusUpdate.from_push({"params": {"deviceName": "PB01"}}) is None
    assert StatusUpdate.from_push({}) is None
