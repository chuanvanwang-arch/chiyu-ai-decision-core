"""第0闸决策凭证 + gate_write 入口（Batch-1a）。

含 parity 形态（消费方经 foundation 契约接入第0闸）与变异自证（删判据→转红→还原）。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.gate import (
    DecisionCredentialError, DecisionRequiredError, require_decision_id,
    verify_decision_credential,
)
from chiyu_kernel.gate import gate_write


def _cred(did="d1", issuer="crm", checksum="x9"):
    return {"decision_id": did, "issuer": issuer,
            "issued_at": "t", "ttl": 0, "checksum": checksum}


def test_require_decision_id_missing_raises():
    with pytest.raises(DecisionRequiredError):
        require_decision_id({})


def test_require_decision_id_empty_raises():
    with pytest.raises(DecisionRequiredError):
        require_decision_id({"decision_id": "  "})


def test_require_decision_id_present_returns():
    assert require_decision_id({"decision_id": "d42"}) == "d42"


def test_verify_credential_missing_field_raises():
    bad = _cred()
    del bad["checksum"]
    with pytest.raises(DecisionCredentialError):
        verify_decision_credential(bad)


def test_verify_credential_bad_checksum_raises():
    with pytest.raises(DecisionCredentialError):
        verify_decision_credential(_cred(checksum=""))


def test_verify_credential_bad_issuer_raises():
    with pytest.raises(DecisionCredentialError):
        verify_decision_credential(_cred(issuer=""))


def test_verify_credential_valid_returns():
    assert verify_decision_credential(_cred()) == "d1"


def test_gate_write_payload_form():
    assert gate_write({"decision_id": "d7"}) == "d7"


def test_gate_write_missing_raises():
    with pytest.raises(DecisionRequiredError):
        gate_write({})


def test_gate_write_credential_form():
    assert gate_write({}, decision_cred=_cred(did="d9")) == "d9"


def test_gate_write_on_missing_return_none():
    assert gate_write({}, on_missing="return_none") is None
