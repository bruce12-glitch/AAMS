"""SRMIST-only gate: only @srmist.edu.in is ever accepted."""

from app.auth import is_srmist_email, normalize_email, reject_non_srmist


def test_accepts_srmist_case_insensitive():
    assert is_srmist_email('Test@SRMIST.EDU.IN')
    assert is_srmist_email('  abc@srmist.edu.in  ')


def test_rejects_other_domains():
    assert not is_srmist_email('x@gmail.com')
    assert not is_srmist_email('x@srmist.edu')
    assert not is_srmist_email('x@srmist.edu.in.evil.com')
    assert not is_srmist_email('')


def test_normalize_trims_and_lowers():
    assert normalize_email('  AbC@SRMIST.EDU.IN ') == 'abc@srmist.edu.in'


def test_reject_helper_raises_clear_error():
    try:
        reject_non_srmist('x@gmail.com')
        assert False, 'should have raised'
    except ValueError as exc:
        assert 'srmist.edu.in' in str(exc).lower()
