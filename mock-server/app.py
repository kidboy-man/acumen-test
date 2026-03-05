import json
import logging
import os
from pathlib import Path

from flask import Flask, abort, jsonify, request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mock_server.log') if os.environ.get('LOG_TO_FILE') else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

DATA_FILE = Path(__file__).resolve().parent / "data" / "customers.json"
_customers_cache = None


def load_customers():
    global _customers_cache
    if _customers_cache is None:
        try:
            if not DATA_FILE.exists():
                logger.error(f"Data file not found: {DATA_FILE}")
                raise FileNotFoundError(f"Data file not found: {DATA_FILE}")
            with open(DATA_FILE, encoding="utf-8") as f:
                _customers_cache = json.load(f)
            logger.info(f"Loaded {len(_customers_cache)} customers from {DATA_FILE}")
        except Exception as e:
            logger.error(f"Failed to load customers data: {e}")
            raise
    return _customers_cache


def get_customer_by_id(customer_id):
    try:
        customers = load_customers()
        for c in customers:
            if c.get("customer_id") == customer_id:
                logger.debug(f"Found customer: {customer_id}")
                return c
        logger.warning(f"Customer not found: {customer_id}")
        return None
    except Exception as e:
        logger.error(f"Error searching for customer {customer_id}: {e}")
        raise


@app.route("/api/health", methods=["GET"])
def health():
    logger.debug("Health check requested")
    return jsonify({"status": "ok"})


@app.route("/api/customers", methods=["GET"])
def list_customers():
    try:
        customers = load_customers()
        total = len(customers)

        page = max(1, request.args.get("page", 1, type=int))
        limit = max(1, min(100, request.args.get("limit", 10, type=int)))

        start = (page - 1) * limit
        end = start + limit
        data = customers[start:end]

        logger.info(f"Returning {len(data)} customers (page {page}, limit {limit}) from total {total}")

        return jsonify({
            "data": data,
            "total": total,
            "page": page,
            "limit": limit,
        })
    except Exception as e:
        logger.error(f"Error in list_customers: {e}", exc_info=True)
        abort(500, description="Internal server error")


@app.route("/api/customers/<customer_id>", methods=["GET"])
def get_customer(customer_id):
    try:
        customer = get_customer_by_id(customer_id)
        if customer is None:
            logger.warning(f"Customer not found: {customer_id}")
            abort(404, description="Customer not found")
        
        logger.info(f"Returning customer: {customer_id}")
        return jsonify(customer)
    except Exception as e:
        logger.error(f"Error in get_customer for {customer_id}: {e}", exc_info=True)
        abort(500, description="Internal server error")


@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {error}")
    return jsonify({"error": "Not found", "message": str(error)}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}", exc_info=True)
    return jsonify({"error": "Internal server error", "message": str(error)}), 500


@app.before_request
def log_request_info():
    logger.debug(f"Request: {request.method} {request.url} from {request.remote_addr}")


@app.after_request
def log_response_info(response):
    logger.debug(f"Response: {response.status_code} for {request.method} {request.url}")
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
