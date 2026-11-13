import os
import threading
import time
from types import SimpleNamespace

from sqlalchemy.exc import SQLAlchemyError

from app.metrics import RULES_STALE_SERVED
from app.models import Promotion

# Promotion rules change rarely, so cache them briefly. 0 disables the cache.
RULES_CACHE_TTL_SECONDS = float(os.getenv("RULES_CACHE_TTL_SECONDS", "30"))
# After a failed refresh, keep serving the last rules and retry after this long.
RULES_STALE_RETRY_SECONDS = float(os.getenv("RULES_STALE_RETRY_SECONDS", "5"))

_cache = {"expires_at": 0.0, "rows": None}
_refresh_lock = threading.Lock()

def _query_rules(db):
    return [
        SimpleNamespace(
            id=p.id,
            description=p.description,
            discount_percent=p.discount_percent,
            minimum_purchases=p.minimum_purchases,
            minimum_spend=p.minimum_spend,
            active=p.active,
        )
        for p in db.query(Promotion).filter(Promotion.active.is_(True)).all()
    ]

def load_promotions(db):
    # Active promotion rules cached and resilient to a slow or failing rules query
    
    if RULES_CACHE_TTL_SECONDS <= 0:
        return _query_rules(db)

    if time.monotonic() < _cache["expires_at"]:
        return _cache["rows"]

    have_stale = _cache["rows"] is not None

    # With stale rules available, only one request refreshes. The rest keep
    # using them, so a slow rules table cannot pin the whole connection pool.
    if have_stale and not _refresh_lock.acquire(blocking=False):
        return _cache["rows"]

    try:
        rows = _query_rules(db)
        _cache["rows"] = rows
        _cache["expires_at"] = time.monotonic() + RULES_CACHE_TTL_SECONDS
        return rows
    except SQLAlchemyError:
        if not have_stale:
            raise
        RULES_STALE_SERVED.inc()
        _cache["expires_at"] = time.monotonic() + RULES_STALE_RETRY_SECONDS
        return _cache["rows"]
    finally:
        if have_stale:
            _refresh_lock.release()