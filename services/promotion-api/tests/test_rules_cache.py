import pytest
from prometheus_client import REGISTRY
from sqlalchemy.exc import OperationalError

from app import rules_cache

@pytest.fixture(autouse=True)
def reset_cache(monkeypatch):
    rules_cache._cache.update(rows=None, expires_at=0.0)
    monkeypatch.setattr(rules_cache, "RULES_CACHE_TTL_SECONDS", 30.0)

def stale_count():
    return REGISTRY.get_sample_value("rules_cache_stale_served_total") or 0.0

def test_rules_are_cached_within_ttl(monkeypatch):
    calls = []
    monkeypatch.setattr(rules_cache, "_query_rules", lambda db: calls.append(1) or ["rule"])

    assert rules_cache.load_promotions(None) == ["rule"]
    assert rules_cache.load_promotions(None) == ["rule"]
    assert len(calls) == 1

def test_stale_rules_served_when_refresh_fails(monkeypatch):
    monkeypatch.setattr(rules_cache, "_query_rules", lambda db: ["rule"])
    rules_cache.load_promotions(None)
    rules_cache._cache["expires_at"] = 0.0  # force expiry

    def failing(db):
        raise OperationalError("select", {}, Exception("statement timeout"))

    monkeypatch.setattr(rules_cache, "_query_rules", failing)
    before = stale_count()

    assert rules_cache.load_promotions(None) == ["rule"]
    assert stale_count() == before + 1

def test_error_propagates_when_no_stale_rules(monkeypatch):
    def failing(db):
        raise OperationalError("select", {}, Exception("down"))

    monkeypatch.setattr(rules_cache, "_query_rules", failing)

    with pytest.raises(OperationalError):
        rules_cache.load_promotions(None)

def test_ttl_zero_disables_cache(monkeypatch):
    monkeypatch.setattr(rules_cache, "RULES_CACHE_TTL_SECONDS", 0.0)
    calls = []
    monkeypatch.setattr(rules_cache, "_query_rules", lambda db: calls.append(1) or ["rule"])

    rules_cache.load_promotions(None)
    rules_cache.load_promotions(None)
    assert len(calls) == 2