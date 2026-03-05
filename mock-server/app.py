import json
import os
from pathlib import Path

from flask import Flask, abort, jsonify, request

app = Flask(__name__)

DATA_FILE = Path(__file__).resolve().parent / "data" / "customers.json"
_customers_cache = None


def load_customers():
    global _customers_cache
    if _customers_cache is None:
        if not DATA_FILE.exists():
            raise FileNotFoundError(f"Data file not found: {DATA_FILE}")
        with open(DATA_FILE, encoding="utf-8") as f:
            _customers_cache = json.load(f)
    return _customers_cache


def get_customer_by_id(customer_id):
    customers = load_customers()
    for c in customers:
        if c.get("customer_id") == customer_id:
            return c
    return None


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/customers", methods=["GET"])
def list_customers():
    customers = load_customers()
    total = len(customers)

    page = max(1, request.args.get("page", 1, type=int))
    limit = max(1, min(100, request.args.get("limit", 10, type=int)))

    start = (page - 1) * limit
    end = start + limit
    data = customers[start:end]

    return jsonify({
        "data": data,
        "total": total,
        "page": page,
        "limit": limit,
    })


@app.route("/api/customers/<customer_id>", methods=["GET"])
def get_customer(customer_id):
    customer = get_customer_by_id(customer_id)
    if customer is None:
        abort(404, description="Customer not found")
    return jsonify(customer)


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": error.description or "Not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
