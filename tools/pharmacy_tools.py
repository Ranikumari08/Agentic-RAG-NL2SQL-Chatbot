"""
pharmacy_tool.py
Looks up real medication rows from Postgres (medications table, loaded
from medications.csv).

medications.csv stores each medicine as multiple numbered SKUs
(e.g. "Metformin 5", "Metformin 31", "Metformin 46" ...), each with its
own manufacturer/price/stock — there is no plain "Metformin" row. So an
exact-match lookup on the generic name always fails; this tool instead
does a partial (ILIKE) match on the generic name, aggregates stock
across all matching SKUs, and returns the cheapest in-stock SKU as the
recommended pick plus the full list of matches for the agent/patient to
choose from.

Schema assumed:
  medications(medication_id, medication_name, category, manufacturer,
              unit_price, stock_quantity)
"""

from typing import Dict, Any
from db import get_cursor


def check_medicine_availability(medicine_name: str, quantity: int) -> Dict[str, Any]:

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT medication_id, medication_name, manufacturer,
                   unit_price, stock_quantity
            FROM medications
            WHERE medication_name ILIKE %s
            ORDER BY unit_price ASC
            """,
            (f"%{medicine_name}%",),
        )
        matches = cur.fetchall()

    if not matches:
        return {
            "status": "error",
            "message": f"Medicine '{medicine_name}' not found.",
        }

    total_stock = sum(row["stock_quantity"] for row in matches)
    best = matches[0]  # cheapest match; swap to max(stock_quantity) if preferred

    return {
        "status": "success",
        "medicine": medicine_name,
        "requested_quantity": quantity,
        "recommended_sku": {
            "medication_id": best["medication_id"],
            "medication_name": best["medication_name"],
            "manufacturer": best["manufacturer"],
            "price_per_unit": float(best["unit_price"]),
            "available_quantity": best["stock_quantity"],
        },
        "total_available_quantity_all_skus": total_stock,
        "available": best["stock_quantity"] >= quantity,
        "matching_skus": [
            {
                "medication_id": row["medication_id"],
                "medication_name": row["medication_name"],
                "manufacturer": row["manufacturer"],
                "price_per_unit": float(row["unit_price"]),
                "available_quantity": row["stock_quantity"],
            }
            for row in matches
        ],
    }