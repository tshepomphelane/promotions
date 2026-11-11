from decimal import Decimal
from types import SimpleNamespace

from app.eligibility import evaluate_eligibility

def test_customer_qualifies_for_promotion():
    activity = SimpleNamespace(
        purchase_count=5,
        total_spend=Decimal("1500.00")
    )

    promotion = SimpleNamespace(
        id = "WELCOME001",
        description = "Welcome discount",
        discount_percent=10,
        minimum_purchases=3,
        minimum_spend=Decimal("1000.00"),
        active=True
    )

    result = evaluate_eligibility(activity, [promotion])

    assert len(result) == 1
    assert result[0]["promotion_id"] == "WELCOME001"

def test_customer_does_not_qualify():    
    activity = SimpleNamespace(
        purchase_count=1,
        total_spend=Decimal("100.00")
    )

    promotion = SimpleNamespace(
        id = "WELCOME001",
        description = "Welcome discount",
        discount_percent=10,
        minimum_purchases=3,
        minimum_spend=Decimal("1000.00"),
        active=True
    )

    result = evaluate_eligibility(activity, [promotion])

    assert result == []