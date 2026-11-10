from decimal import Decimal

def evaluate_eligibility(activity, promotions):
    eligible = []

    for promotion in promotions:
        if not promotion.active:
            continue

        if activity.purchase_count < promotion.minimum_purchase:
            continue

        if activity.total_spend < Decimal(str(promotion.minimum_spend)):
            continue

        eligible.append({
            "promotion_id":promotion.id,
            "description":promotion.description,
            "discount_percent": promotion.discount_percent,
            "reason": "Customer meets activity requirement"
        })
    return eligible
