from types import SimpleNamespace

import pytest

from scripts.embed_bns_chunks import (
    validate_bns_chunk_scope,
)


def test_validate_bns_chunk_scope_accepts_bns():
    chunks = [
        SimpleNamespace(
            document_id=2,
            act_id=1,
            version_id=1,
        )
    ]

    validate_bns_chunk_scope(
        chunks
    )


def test_validate_bns_chunk_scope_rejects_other_document():
    chunks = [
        SimpleNamespace(
            document_id=3,
            act_id=2,
            version_id=2,
        )
    ]

    with pytest.raises(
        RuntimeError
    ):
        validate_bns_chunk_scope(
            chunks
        )


def test_validate_bns_chunk_scope_rejects_wrong_version():
    chunks = [
        SimpleNamespace(
            document_id=2,
            act_id=1,
            version_id=99,
        )
    ]

    with pytest.raises(
        RuntimeError
    ):
        validate_bns_chunk_scope(
            chunks
        )