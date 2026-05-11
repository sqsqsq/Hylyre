"""L1: cert bootstrap messaging."""

from pathlib import Path

from hylyre.drivers.lyrebird.cert_bootstrap import mitm_trust_instructions


def test_mitm_instructions_mentions_hdc_and_serial() -> None:
    text = mitm_trust_instructions(
        ca_cert=Path("C:/fake/ca.pem"),
        hdc_serial="DEVSN",
    )
    assert "DEVSN" in text
    assert "ca.pem" in text
