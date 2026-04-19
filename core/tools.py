import json
from pathlib import Path
from datetime import datetime, timedelta
import re
from functools import lru_cache
import random
import time
from typing import Any, Dict, Optional

BASE = Path('data')

EXPECTED_SCHEMAS = {
    'get_customer': {'customer_id', 'name', 'email', 'tier', 'member_since', 'total_orders', 'total_spent', 'address'},
    'get_order': {'order_id', 'customer_id', 'product_id', 'status', 'order_date', 'delivery_date', 'return_deadline', 'refund_status', 'amount', 'notes'},
    'get_product': {'product_id', 'name', 'category', 'price', 'warranty_months', 'return_window_days', 'returnable', 'notes'},
    'check_refund_eligibility': {'eligible', 'reason', 'error'},
    'issue_refund': {'success', 'message', 'refund_id', 'error'},
    'send_reply': {'success', 'message', 'error'},
    'escalate': {'success', 'message', 'error'},
}


def validate_tool_output(tool_name: str, output: Any) -> Any:
    if tool_name in {'get_customer', 'get_order', 'get_product'}:
        if output is None:
            return None
        if not isinstance(output, dict):
            raise ValueError(f"{tool_name} returned malformed data: expected dict or None")
        missing = EXPECTED_SCHEMAS[tool_name] - set(output.keys())
        if missing:
            raise ValueError(f"{tool_name} missing expected keys: {missing}")
        return output

    if tool_name == 'search_knowledge_base':
        if not isinstance(output, str):
            raise ValueError('search_knowledge_base returned malformed data: expected string')
        return output

    if tool_name in EXPECTED_SCHEMAS:
        if not isinstance(output, dict):
            raise ValueError(f"{tool_name} returned malformed data: expected dict")
        missing = EXPECTED_SCHEMAS[tool_name] - set(output.keys())
        if missing:
            raise ValueError(f"{tool_name} missing expected keys: {missing}")
        return output

    return output


@lru_cache(maxsize=128)
def load_json(name: str) -> Any:
    with open(BASE / name, 'r') as f:
        return json.load(f)


@lru_cache(maxsize=128)
def get_customer(email: str) -> Optional[Dict[str, Any]]:
    customers = load_json('customers.json')
    for c in customers:
        if c['email'] == email:
            return validate_tool_output('get_customer', c)
    return None


@lru_cache(maxsize=128)
def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    orders = load_json('orders.json')
    for o in orders:
        if o['order_id'] == order_id:
            return validate_tool_output('get_order', o)
    return None


@lru_cache(maxsize=128)
def get_product(product_id: str) -> Optional[Dict[str, Any]]:
    products = load_json('products.json')
    for p in products:
        if p['product_id'] == product_id:
            return validate_tool_output('get_product', p)
    return None


def search_knowledge_base(query: str) -> str:
    with open(BASE / 'knowledge-base.md', 'r') as f:
        kb = f.read().lower()
    query = query.lower()

    if random.random() < 0.05:
        time.sleep(0.1)
        raise ValueError('Knowledge base search timeout')

    if 'return' in query and 'policy' in query:
        return validate_tool_output('search_knowledge_base', 'Return Policy: Standard 30-day return window. Electronics accessories 60 days, high-value electronics 15 days. Non-returnable if registered online.')
    if 'refund' in query:
        return validate_tool_output('search_knowledge_base', 'Refund Policy: Processed within 5-7 business days after eligibility check. Cannot be reversed once issued.')
    if 'warranty' in query:
        return validate_tool_output('search_knowledge_base', 'Warranty: Covers manufacturing defects only. Electronics: 12 months, Home appliances: 24 months, Accessories: 6 months.')
    if 'cancel' in query:
        return validate_tool_output('search_knowledge_base', 'Cancellation: Processing orders can be cancelled free of charge. Shipped orders cannot.')
    if 'escalate' in query or 'fraud' in query:
        return validate_tool_output('search_knowledge_base', 'Escalate: Warranty claims, replacement requests, refunds >$200, fraud signs, low confidence (<0.6), conflicting data.')
    if 'vip' in query or 'tier' in query:
        return validate_tool_output('search_knowledge_base', 'Customer Tiers: Standard (no exceptions), Premium (judgment for borderline cases), VIP (extended leniency, check notes for pre-approvals).')
    return validate_tool_output('search_knowledge_base', 'No relevant policy found. Please rephrase your query.')


def check_refund_eligibility(order_id: str) -> Dict[str, Any]:
    if random.random() < 0.08:
        time.sleep(0.2)
        return validate_tool_output('check_refund_eligibility', {'eligible': False, 'reason': 'Eligibility check service temporarily unavailable', 'error': True})

    order = get_order(order_id)
    if not order:
        return validate_tool_output('check_refund_eligibility', {'eligible': False, 'reason': 'Order not found', 'error': False})

    if order['refund_status'] == 'refunded':
        return validate_tool_output('check_refund_eligibility', {'eligible': False, 'reason': 'Refund already processed', 'error': False})

    if order['status'] != 'delivered':
        return validate_tool_output('check_refund_eligibility', {'eligible': False, 'reason': 'Order not yet delivered', 'error': False})

    if order['return_deadline']:
        deadline = datetime.fromisoformat(order['return_deadline'])
        if datetime.now() > deadline:
            return validate_tool_output('check_refund_eligibility', {'eligible': False, 'reason': 'Past return deadline', 'error': False})

    return validate_tool_output('check_refund_eligibility', {'eligible': True, 'reason': 'Eligible for refund', 'error': False})


def issue_refund(order_id: str, amount: float) -> Dict[str, Any]:
    if random.random() < 0.1:
        time.sleep(0.3)
        return validate_tool_output('issue_refund', {'success': False, 'message': 'Refund service timeout', 'refund_id': None, 'error': True})

    order = get_order(order_id)
    if not order:
        return validate_tool_output('issue_refund', {'success': False, 'message': 'Order not found', 'refund_id': None, 'error': False})

    eligibility = check_refund_eligibility(order_id)
    if not eligibility['eligible']:
        return validate_tool_output('issue_refund', {'success': False, 'message': eligibility['reason'], 'refund_id': None, 'error': False})

    refund_id = f"REF-{order_id.split('-')[1]}-{random.randint(1000,9999)}"
    return validate_tool_output('issue_refund', {'success': True, 'message': f'Refund of ${amount} issued', 'refund_id': refund_id, 'error': False})


def send_reply(ticket_id: str, message: str) -> Dict[str, Any]:
    if random.random() < 0.03:
        time.sleep(0.1)
        return validate_tool_output('send_reply', {'success': False, 'message': 'Email service unavailable', 'error': True})

    return validate_tool_output('send_reply', {'success': True, 'message': f'Reply sent for ticket {ticket_id}', 'error': False})


def escalate(ticket_id: str, summary: str, priority: str) -> Dict[str, Any]:
    if random.random() < 0.02:
        time.sleep(0.1)
        return validate_tool_output('escalate', {'success': False, 'message': 'Escalation service error', 'error': True})

    return validate_tool_output('escalate', {'success': True, 'message': f'Ticket {ticket_id} escalated with {priority} priority', 'error': False})


def extract_order_id(text: str) -> Optional[str]:
    match = re.search(r'ORD-\d+', text)
    return match.group() if match else None


def calculate_confidence(action: str, factors: list) -> float:
    base_conf = 0.8
    if 'clear_policy' in factors:
        base_conf += 0.1
    if 'customer_verified' in factors:
        base_conf += 0.05
    if 'order_found' in factors:
        base_conf += 0.05
    if 'escalation_needed' in factors:
        base_conf -= 0.2
    return min(max(base_conf, 0.0), 1.0)
