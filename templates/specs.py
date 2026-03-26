"""Pre-built data specification templates for common use cases."""
from __future__ import annotations

from core.types import DataSpec, DataType, FieldSpec

# ── E-Commerce Templates ────────────────────────────────────────────────────

ECOMMERCE_ORDERS = DataSpec(
    data_type=DataType.TABULAR,
    name="ecommerce_orders",
    row_count=1000,
    fields=[
        FieldSpec(name="order_id", dtype="str", unique=True, description="Unique order identifier"),
        FieldSpec(name="customer_id", dtype="str", description="Customer identifier"),
        FieldSpec(name="customer_name", dtype="str", description="Customer full name"),
        FieldSpec(name="customer_email", dtype="str", description="Customer email address"),
        FieldSpec(name="product_name", dtype="str", description="Product name"),
        FieldSpec(name="product_category", dtype="category", 
                 categories=["Electronics", "Clothing", "Home & Garden", "Books", "Sports", "Toys"]),
        FieldSpec(name="quantity", dtype="int", min_val=1, max_val=10),
        FieldSpec(name="unit_price", dtype="float", min_val=5.0, max_val=999.99),
        FieldSpec(name="total_amount", dtype="float", min_val=5.0, max_val=9999.99),
        FieldSpec(name="currency", dtype="category", categories=["USD", "EUR", "GBP", "TRY"]),
        FieldSpec(name="order_status", dtype="category", 
                 categories=["pending", "processing", "shipped", "delivered", "cancelled", "returned"]),
        FieldSpec(name="payment_method", dtype="category", 
                 categories=["credit_card", "debit_card", "paypal", "bank_transfer", "cash_on_delivery"]),
        FieldSpec(name="shipping_address", dtype="str", description="Shipping address"),
        FieldSpec(name="order_date", dtype="datetime", min_val="2023-01-01T00:00:00", max_val="2024-12-31T23:59:59"),
        FieldSpec(name="delivery_date", dtype="datetime", min_val="2023-01-01T00:00:00", max_val="2025-01-31T23:59:59", nullable=True),
    ],
    constraints=["delivery_date > order_date", "total_amount = quantity * unit_price"],
    context="E-commerce platform order data with customer and product information",
    locale="en_US",
)

ECOMMERCE_PRODUCTS = DataSpec(
    data_type=DataType.TABULAR,
    name="ecommerce_products",
    row_count=500,
    fields=[
        FieldSpec(name="product_id", dtype="str", unique=True, description="Unique product identifier"),
        FieldSpec(name="sku", dtype="str", unique=True, description="Stock keeping unit"),
        FieldSpec(name="name", dtype="str", description="Product name"),
        FieldSpec(name="description", dtype="str", description="Product description"),
        FieldSpec(name="category", dtype="category", 
                 categories=["Electronics", "Clothing", "Home & Garden", "Books", "Sports", "Toys", "Beauty", "Food"]),
        FieldSpec(name="subcategory", dtype="str", description="Product subcategory"),
        FieldSpec(name="brand", dtype="str", description="Brand name"),
        FieldSpec(name="price", dtype="float", min_val=1.0, max_val=9999.99),
        FieldSpec(name="cost", dtype="float", min_val=0.5, max_val=5000.0),
        FieldSpec(name="stock_quantity", dtype="int", min_val=0, max_val=10000),
        FieldSpec(name="weight_kg", dtype="float", min_val=0.01, max_val=100.0),
        FieldSpec(name="is_active", dtype="bool"),
        FieldSpec(name="rating", dtype="float", min_val=1.0, max_val=5.0),
        FieldSpec(name="review_count", dtype="int", min_val=0, max_val=5000),
        FieldSpec(name="created_at", dtype="datetime"),
    ],
    constraints=["price > cost"],
    context="E-commerce product catalog with pricing and inventory",
    locale="en_US",
)


# ── User Data Templates ─────────────────────────────────────────────────────

USER_PROFILES = DataSpec(
    data_type=DataType.TABULAR,
    name="user_profiles",
    row_count=1000,
    fields=[
        FieldSpec(name="user_id", dtype="str", unique=True),
        FieldSpec(name="username", dtype="str", unique=True),
        FieldSpec(name="email", dtype="str", unique=True),
        FieldSpec(name="first_name", dtype="str"),
        FieldSpec(name="last_name", dtype="str"),
        FieldSpec(name="phone", dtype="str", nullable=True),
        FieldSpec(name="date_of_birth", dtype="datetime", min_val="1950-01-01", max_val="2005-12-31"),
        FieldSpec(name="gender", dtype="category", categories=["male", "female", "other", "prefer_not_to_say"]),
        FieldSpec(name="country", dtype="str"),
        FieldSpec(name="city", dtype="str"),
        FieldSpec(name="address", dtype="str"),
        FieldSpec(name="postal_code", dtype="str"),
        FieldSpec(name="account_status", dtype="category", categories=["active", "inactive", "suspended", "pending"]),
        FieldSpec(name="subscription_tier", dtype="category", categories=["free", "basic", "premium", "enterprise"]),
        FieldSpec(name="created_at", dtype="datetime"),
        FieldSpec(name="last_login", dtype="datetime", nullable=True),
    ],
    context="User profile data for a SaaS application",
    locale="en_US",
)


# ── Server Metrics Templates ────────────────────────────────────────────────

SERVER_METRICS = DataSpec(
    data_type=DataType.TIMESERIES,
    name="server_metrics",
    row_count=10000,
    fields=[
        FieldSpec(name="timestamp", dtype="datetime", min_val="2024-01-01T00:00:00", max_val="2024-01-07T23:59:59"),
        FieldSpec(name="server_id", dtype="category", categories=["srv-001", "srv-002", "srv-003", "srv-004"]),
        FieldSpec(name="cpu_usage_percent", dtype="float", min_val=0, max_val=100),
        FieldSpec(name="memory_used_gb", dtype="float", min_val=0, max_val=64),
        FieldSpec(name="memory_total_gb", dtype="float", min_val=16, max_val=64),
        FieldSpec(name="disk_usage_percent", dtype="float", min_val=0, max_val=100),
        FieldSpec(name="network_in_mbps", dtype="float", min_val=0, max_val=1000),
        FieldSpec(name="network_out_mbps", dtype="float", min_val=0, max_val=1000),
        FieldSpec(name="active_connections", dtype="int", min_val=0, max_val=10000),
        FieldSpec(name="request_count", dtype="int", min_val=0, max_val=50000),
        FieldSpec(name="error_count", dtype="int", min_val=0, max_val=1000),
        FieldSpec(name="response_time_ms", dtype="float", min_val=1, max_val=5000),
    ],
    constraints=["memory_used_gb <= memory_total_gb"],
    context="Real-time server monitoring data with 1-minute sampling",
    locale="en_US",
)

IOT_SENSOR_DATA = DataSpec(
    data_type=DataType.TIMESERIES,
    name="iot_sensor_data",
    row_count=5000,
    fields=[
        FieldSpec(name="timestamp", dtype="datetime"),
        FieldSpec(name="device_id", dtype="category", 
                 categories=["sensor-001", "sensor-002", "sensor-003", "sensor-004", "sensor-005"]),
        FieldSpec(name="temperature_celsius", dtype="float", min_val=-20, max_val=50),
        FieldSpec(name="humidity_percent", dtype="float", min_val=0, max_val=100),
        FieldSpec(name="pressure_hpa", dtype="float", min_val=950, max_val=1050),
        FieldSpec(name="battery_level", dtype="float", min_val=0, max_val=100),
        FieldSpec(name="signal_strength_dbm", dtype="int", min_val=-100, max_val=-30),
        FieldSpec(name="is_alert", dtype="bool"),
    ],
    context="IoT environmental sensor readings",
    locale="en_US",
)


# ── Log Templates ───────────────────────────────────────────────────────────

HTTP_ACCESS_LOGS = DataSpec(
    data_type=DataType.LOG,
    name="http_access_logs",
    row_count=5000,
    fields=[
        FieldSpec(name="timestamp", dtype="datetime"),
        FieldSpec(name="method", dtype="category", categories=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]),
        FieldSpec(name="path", dtype="str"),
        FieldSpec(name="status_code", dtype="int", min_val=100, max_val=599),
        FieldSpec(name="response_time_ms", dtype="int", min_val=1, max_val=30000),
        FieldSpec(name="bytes_sent", dtype="int", min_val=0, max_val=10000000),
        FieldSpec(name="client_ip", dtype="str"),
        FieldSpec(name="user_agent", dtype="str"),
        FieldSpec(name="referer", dtype="str", nullable=True),
        FieldSpec(name="user_id", dtype="str", nullable=True),
        FieldSpec(name="session_id", dtype="str"),
        FieldSpec(name="request_id", dtype="str", unique=True),
    ],
    context="HTTP API access logs for web application",
    locale="en_US",
)

APPLICATION_LOGS = DataSpec(
    data_type=DataType.LOG,
    name="application_logs",
    row_count=2000,
    fields=[
        FieldSpec(name="timestamp", dtype="datetime"),
        FieldSpec(name="level", dtype="category", categories=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
        FieldSpec(name="service", dtype="category", 
                 categories=["api-gateway", "auth-service", "user-service", "payment-service", "notification-service"]),
        FieldSpec(name="message", dtype="str"),
        FieldSpec(name="trace_id", dtype="str"),
        FieldSpec(name="span_id", dtype="str"),
        FieldSpec(name="user_id", dtype="str", nullable=True),
        FieldSpec(name="error_code", dtype="str", nullable=True),
        FieldSpec(name="stack_trace", dtype="str", nullable=True),
    ],
    context="Microservices application logs with distributed tracing",
    locale="en_US",
)


# ── NLP Templates ───────────────────────────────────────────────────────────

PRODUCT_REVIEWS = DataSpec(
    data_type=DataType.NLP,
    name="product_reviews",
    row_count=500,
    fields=[
        FieldSpec(name="review_id", dtype="str", unique=True),
        FieldSpec(name="product_id", dtype="str"),
        FieldSpec(name="product_name", dtype="str"),
        FieldSpec(name="user_id", dtype="str"),
        FieldSpec(name="user_name", dtype="str"),
        FieldSpec(name="rating", dtype="int", min_val=1, max_val=5),
        FieldSpec(name="title", dtype="str", description="Review title/headline"),
        FieldSpec(name="review_text", dtype="str", description="Detailed review content"),
        FieldSpec(name="pros", dtype="str", description="Positive aspects mentioned"),
        FieldSpec(name="cons", dtype="str", description="Negative aspects mentioned"),
        FieldSpec(name="sentiment", dtype="category", categories=["positive", "negative", "neutral", "mixed"]),
        FieldSpec(name="helpful_votes", dtype="int", min_val=0, max_val=1000),
        FieldSpec(name="verified_purchase", dtype="bool"),
        FieldSpec(name="created_at", dtype="datetime"),
    ],
    context="E-commerce product reviews with sentiment analysis",
    locale="en_US",
)

SUPPORT_TICKETS = DataSpec(
    data_type=DataType.NLP,
    name="support_tickets",
    row_count=300,
    fields=[
        FieldSpec(name="ticket_id", dtype="str", unique=True),
        FieldSpec(name="customer_id", dtype="str"),
        FieldSpec(name="customer_name", dtype="str"),
        FieldSpec(name="customer_email", dtype="str"),
        FieldSpec(name="subject", dtype="str", description="Ticket subject/title"),
        FieldSpec(name="description", dtype="str", description="Detailed issue description"),
        FieldSpec(name="category", dtype="category", 
                 categories=["billing", "technical", "account", "shipping", "product", "general"]),
        FieldSpec(name="priority", dtype="category", categories=["low", "medium", "high", "urgent"]),
        FieldSpec(name="status", dtype="category", 
                 categories=["open", "in_progress", "waiting_customer", "resolved", "closed"]),
        FieldSpec(name="assigned_to", dtype="str", nullable=True),
        FieldSpec(name="resolution", dtype="str", nullable=True, description="Resolution notes"),
        FieldSpec(name="created_at", dtype="datetime"),
        FieldSpec(name="resolved_at", dtype="datetime", nullable=True),
    ],
    context="Customer support ticket system with issue tracking",
    locale="en_US",
)


# ── Financial Templates ─────────────────────────────────────────────────────

FINANCIAL_TRANSACTIONS = DataSpec(
    data_type=DataType.TABULAR,
    name="financial_transactions",
    row_count=5000,
    fields=[
        FieldSpec(name="transaction_id", dtype="str", unique=True),
        FieldSpec(name="account_id", dtype="str"),
        FieldSpec(name="transaction_type", dtype="category", 
                 categories=["deposit", "withdrawal", "transfer", "payment", "refund"]),
        FieldSpec(name="amount", dtype="float", min_val=0.01, max_val=100000.0),
        FieldSpec(name="currency", dtype="category", categories=["USD", "EUR", "GBP", "JPY", "TRY"]),
        FieldSpec(name="balance_before", dtype="float", min_val=0, max_val=1000000),
        FieldSpec(name="balance_after", dtype="float", min_val=0, max_val=1000000),
        FieldSpec(name="merchant_name", dtype="str", nullable=True),
        FieldSpec(name="category", dtype="category", 
                 categories=["groceries", "utilities", "entertainment", "transportation", "dining", "shopping", "healthcare"]),
        FieldSpec(name="status", dtype="category", categories=["pending", "completed", "failed", "reversed"]),
        FieldSpec(name="timestamp", dtype="datetime"),
    ],
    context="Banking transaction records for personal finance",
    locale="en_US",
)


# ── Template Registry ───────────────────────────────────────────────────────

TEMPLATES = {
    # E-commerce
    "ecommerce_orders": ECOMMERCE_ORDERS,
    "ecommerce_products": ECOMMERCE_PRODUCTS,
    
    # Users
    "user_profiles": USER_PROFILES,
    
    # Metrics
    "server_metrics": SERVER_METRICS,
    "iot_sensors": IOT_SENSOR_DATA,
    
    # Logs
    "http_logs": HTTP_ACCESS_LOGS,
    "app_logs": APPLICATION_LOGS,
    
    # NLP
    "product_reviews": PRODUCT_REVIEWS,
    "support_tickets": SUPPORT_TICKETS,
    
    # Financial
    "transactions": FINANCIAL_TRANSACTIONS,
}


def list_templates() -> list[str]:
    """List all available template names."""
    return list(TEMPLATES.keys())


def get_template(name: str) -> DataSpec | None:
    """Get a template by name."""
    return TEMPLATES.get(name)


def get_template_info() -> list[dict]:
    """Get information about all templates."""
    return [
        {
            "name": name,
            "type": spec.data_type.value,
            "fields": len(spec.fields),
            "default_rows": spec.row_count,
            "context": spec.context[:60] + "..." if len(spec.context) > 60 else spec.context,
        }
        for name, spec in TEMPLATES.items()
    ]
