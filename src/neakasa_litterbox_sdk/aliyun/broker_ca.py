"""Trust anchor shipped so the MQTT broker's chain can be verified.

``<productKey>.iot-as-mqtt.<region>.aliyuncs.com`` is served by the
``GlobalSign GCC R1 OV TLS CA 2025`` intermediate, which chains to the
1998 ``GlobalSign Root CA`` (R1). That root is gone from current trust
stores — neither ``certifi`` nor Debian's ``ca-certificates`` carries it
anymore — so verifying against the system store alone fails with
``unable to get local issuer certificate``. Shipping the root keeps chain
and hostname validation on instead of disabling it.

Root and intermediate both expire on 2028-01-28; the broker has to move
to a currently-trusted root before then, at which point the system store
takes over and this file can go.
"""

from __future__ import annotations

from pathlib import Path

BROKER_ROOT_CA_PATH: Path = Path(__file__).parent / "certs" / "globalsign_root_ca_r1.pem"
