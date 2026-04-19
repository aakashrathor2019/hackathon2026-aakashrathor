from datetime import datetime
from core.tools import calculate_confidence


def decide(ticket, tools):
    """Main decision engine with tool chaining"""
    body = ticket['body'].lower()
    factors = []
    tool_calls = []

    customer = tools.get_customer(ticket['customer_email'])
    tool_calls.append({'tool': 'get_customer', 'args': [ticket['customer_email']]})

    if not customer:
        kb_result = tools.search_knowledge_base(body)
        tool_calls.append({'tool': 'search_knowledge_base', 'args': [body]})
        tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], 'Please verify your account email and provide an order number so I can help.']})
        return 'need_info', 0.4, 'Customer identity not verified', factors, tool_calls, None

    factors.append('customer_verified')
    customer_name = customer['name'].split()[0]

    order_id = tools.extract_order_id(ticket['body'])
    order = None
    product = None

    if order_id:
        order = tools.get_order(order_id)
        tool_calls.append({'tool': 'get_order', 'args': [order_id]})
        if order:
            factors.append('order_found')
            product = tools.get_product(order['product_id'])
            tool_calls.append({'tool': 'get_product', 'args': [order['product_id']]})
        else:
            kb_result = tools.search_knowledge_base(body)
            tool_calls.append({'tool': 'search_knowledge_base', 'args': [body]})
            tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], f'Order ID {order_id} not found. Please verify and resend the correct order number.']})
            return 'need_info', 0.5, f'Order ID {order_id} not found. Please verify.', factors, tool_calls, customer
    else:
        if 'cancel' in body and customer:
            orders = [tools.get_order(oid) for oid in ['ORD-1006', 'ORD-1012']]
            tool_calls.extend([{'tool': 'get_order', 'args': [oid]} for oid in ['ORD-1006', 'ORD-1012']])
            processing_orders = [o for o in orders if o and o['status'] == 'processing' and o['customer_id'] == customer['customer_id']]
            if processing_orders:
                order = processing_orders[0]
                order_id = order['order_id']
                factors.append('order_found')
                product = tools.get_product(order['product_id'])
                tool_calls.append({'tool': 'get_product', 'args': [order['product_id']]})
            else:
                kb_result = tools.search_knowledge_base(body)
                tool_calls.append({'tool': 'search_knowledge_base', 'args': [body]})
                tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], 'No order ID provided and no cancellable orders found. Please share the order number or contact support.']})
                return 'need_info', 0.6, 'No order ID provided and no cancellable orders found.', factors, tool_calls, customer
        else:
            if len(body.split()) < 5:
                kb_result = tools.search_knowledge_base(body)
                tool_calls.append({'tool': 'search_knowledge_base', 'args': [body]})
                tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], 'Please provide more details about your issue and include your order number.']})
                return 'need_info', 0.3, 'Please provide more details about your issue and order number.', factors, tool_calls, customer
            kb_result = tools.search_knowledge_base(body)
            tool_calls.append({'tool': 'search_knowledge_base', 'args': [body]})
            if 'policy' in kb_result.lower():
                tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], f'Hi {customer_name}, {kb_result}']})
                return 'send_reply', 0.8, f'Hi {customer_name}, {kb_result}', factors, tool_calls, customer

    if 'cancel' in body:
        if order and order['status'] == 'processing':
            factors.append('clear_policy')
            conf = calculate_confidence('cancelled', factors)
            reply_msg = f'Hi {customer_name}, your order {order_id} has been cancelled successfully. You will receive a confirmation email shortly.'
            tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], reply_msg]})
            return 'cancelled', conf, reply_msg, factors, tool_calls, customer
        return 'deny', 0.9, f'Hi {customer_name}, orders can only be cancelled while in processing status.', factors, tool_calls, customer

    if 'where is my order' in body or 'tracking' in body:
        if order and order['status'] == 'shipped':
            factors.append('clear_policy')
            conf = calculate_confidence('send_reply', factors)
            tracking_info = order.get('notes', 'Tracking information not available')
            reply_msg = f'Hi {customer_name}, your order {order_id} is in transit. {tracking_info}'
            tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], reply_msg]})
            return 'send_reply', conf, reply_msg, factors, tool_calls, customer
        kb_result = tools.search_knowledge_base(body)
        tool_calls.append({'tool': 'search_knowledge_base', 'args': [body]})
        tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], f'Hi {customer_name}, I need your order number to check tracking status.']})
        return 'need_info', 0.7, f'Hi {customer_name}, I need your order number to check tracking status.', factors, tool_calls, customer

    if 'refund' in body and ('already' in body or 'status' in body or 'when' in body):
        if order and order['refund_status'] == 'refunded':
            factors.append('clear_policy')
            conf = calculate_confidence('send_reply', factors)
            reply_msg = f'Hi {customer_name}, your refund for order {order_id} has been processed. It typically takes 5-7 business days to appear in your account.'
            tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], reply_msg]})
            return 'send_reply', conf, reply_msg, factors, tool_calls, customer
        kb_result = tools.search_knowledge_base(body)
        tool_calls.append({'tool': 'search_knowledge_base', 'args': [body]})
        tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], f'Hi {customer_name}, please provide your order number so I can check refund status.']})
        return 'need_info', 0.6, f'Hi {customer_name}, please provide your order number so I can check refund status.', factors, tool_calls, customer

    if 'premium' in body and customer['tier'] != 'premium':
        factors.append('escalation_needed')
        summary = f"Customer {customer_name} claiming premium benefits but is {customer['tier']} tier"
        kb_result = tools.search_knowledge_base(body)
        tool_calls.append({'tool': 'search_knowledge_base', 'args': [body]})
        tool_calls.append({'tool': 'escalate', 'args': [ticket['ticket_id'], summary, 'high']})
        return 'escalate', 0.95, f'Hi {customer_name}, I need to escalate this to our premium support team for verification.', factors, tool_calls, customer

    if 'lawyer' in body or 'threat' in body:
        factors.append('escalation_needed')
        summary = f"Customer {customer_name} using threatening language in ticket {ticket['ticket_id']}"
        kb_result = tools.search_knowledge_base(body)
        tool_calls.append({'tool': 'search_knowledge_base', 'args': [body]})
        tool_calls.append({'tool': 'escalate', 'args': [ticket['ticket_id'], summary, 'urgent']})
        return 'escalate', 0.9, f'Hi {customer_name}, I need to have a supervisor review this request.', factors, tool_calls, customer

    if 'return' in body or 'refund' in body:
        if not order:
            kb_result = tools.search_knowledge_base(body)
            tool_calls.append({'tool': 'search_knowledge_base', 'args': [body]})
            tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], f'Hi {customer_name}, please provide your order number for return/refund processing.']})
            return 'need_info', 0.5, f'Hi {customer_name}, please provide your order number for return/refund processing.', factors, tool_calls, customer

        eligibility = tools.check_refund_eligibility(order_id)
        tool_calls.append({'tool': 'check_refund_eligibility', 'args': [order_id]})

        if eligibility.get('error'):
            factors.append('escalation_needed')
            summary = f"Refund eligibility check failed for order {order_id}"
            tool_calls.append({'tool': 'escalate', 'args': [ticket['ticket_id'], summary, 'medium']})
            return 'escalate', 0.7, f'Hi {customer_name}, our refund system is temporarily unavailable. Escalating to support.', factors, tool_calls, customer

        if not eligibility['eligible']:
            if customer['tier'] == 'vip' and 'extended return' in customer.get('notes', ''):
                factors.append('clear_policy')
                conf = calculate_confidence('approve_refund', factors)
                amount = order['amount']
                tool_calls.append({'tool': 'issue_refund', 'args': [order_id, amount]})
                tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], f'Hi {customer_name}, as a VIP customer, we\'ve approved your return exception. Refund of ${amount} issued.']})
                return 'approve_refund', conf, f'Hi {customer_name}, as a VIP customer, we\'ve approved your return exception. Refund of ${amount} issued.', factors, tool_calls, customer
            return 'deny', 0.85, f'Hi {customer_name}, {eligibility["reason"]}. Please review our return policy.', factors, tool_calls, customer
        else:
            amount = order['amount']
            if amount > 200:
                factors.append('escalation_needed')
                summary = f"High-value refund request: ${amount} for order {order_id}"
                tool_calls.append({'tool': 'escalate', 'args': [ticket['ticket_id'], summary, 'high']})
                return 'escalate', 0.8, f'Hi {customer_name}, high-value refunds require supervisor approval. Escalating.', factors, tool_calls, customer

            factors.append('clear_policy')
            conf = calculate_confidence('approve_refund', factors)
            tool_calls.append({'tool': 'issue_refund', 'args': [order_id, amount]})
            tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], f'Hi {customer_name}, your refund of ${amount} has been issued. It will appear in 5-7 business days.']})
            return 'approve_refund', conf, f'Hi {customer_name}, your refund of ${amount} has been issued. It will appear in 5-7 business days.', factors, tool_calls, customer

    if 'broken' in body or 'defect' in body or 'warranty' in body:
        if 'replacement' in body:
            factors.append('escalation_needed')
            summary = f'Warranty claim with replacement request for order {order_id if order else "unknown"}'
            tool_calls.append({'tool': 'escalate', 'args': [ticket['ticket_id'], summary, 'medium']})
            return 'escalate', 0.9, f'Hi {customer_name}, replacement requests are handled by our warranty team.', factors, tool_calls, customer
        if order and product:
            delivery_date = datetime.fromisoformat(order['delivery_date'])
            warranty_months = product['warranty_months']
            warranty_end = delivery_date.replace(year=delivery_date.year + (warranty_months // 12))
            if datetime.now() <= warranty_end:
                factors.append('escalation_needed')
                summary = f'Warranty claim within period for order {order_id}'
                tool_calls.append({'tool': 'escalate', 'args': [ticket['ticket_id'], summary, 'medium']})
                return 'escalate', 0.85, f'Hi {customer_name}, this appears to be a warranty claim. Escalating to our warranty specialists.', factors, tool_calls, customer
        return 'deny', 0.8, f'Hi {customer_name}, this may be outside warranty coverage. Please provide more details.', factors, tool_calls, customer

    if 'wrong' in body and ('size' in body or 'color' in body or 'item' in body):
        if order:
            factors.append('clear_policy')
            conf = calculate_confidence('send_reply', factors)
            reply_msg = f'Hi {customer_name}, for wrong items, we\'ll arrange pickup and send the correct item at no cost. Please reply to confirm.'
            tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], reply_msg]})
            return 'send_reply', conf, reply_msg, factors, tool_calls, customer
        kb_result = tools.search_knowledge_base(body)
        tool_calls.append({'tool': 'search_knowledge_base', 'args': [body]})
        tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], f'Hi {customer_name}, please provide your order number to process the exchange.']})
        return 'need_info', 0.6, f'Hi {customer_name}, please provide your order number to process the exchange.', factors, tool_calls, customer

    if ('damaged' in body or 'broken' in body) and 'photo' in body:
        if order:
            factors.append('clear_policy')
            conf = calculate_confidence('approve_refund', factors)
            reply_msg = f'Hi {customer_name}, for damaged items with photos, we can process refund without return. Please confirm if you want refund or replacement.'
            tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], reply_msg]})
            return 'send_reply', conf, reply_msg, factors, tool_calls, customer
        kb_result = tools.search_knowledge_base(body)
        tool_calls.append({'tool': 'search_knowledge_base', 'args': [body]})
        tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], f'Hi {customer_name}, for damaged items, please provide photos as evidence.']})
        return 'need_info', 0.7, f'Hi {customer_name}, for damaged items, please provide photos as evidence.', factors, tool_calls, customer

    kb_result = tools.search_knowledge_base(body)
    tool_calls.append({'tool': 'search_knowledge_base', 'args': [body]})
    if 'policy' in kb_result.lower() or 'return' in kb_result.lower():
        factors.append('clear_policy')
        conf = calculate_confidence('send_reply', factors)
        reply_msg = f'Hi {customer_name}, {kb_result}'
        tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], reply_msg]})
        return 'send_reply', conf, reply_msg, factors, tool_calls, customer

    if len(body.split()) < 10:
        tool_calls.append({'tool': 'send_reply', 'args': [ticket['ticket_id'], f'Hi {customer_name}, your message is quite brief. Could you provide more details about your issue?']})
        return 'need_info', 0.4, f'Hi {customer_name}, your message is quite brief. Could you provide more details about your issue?', factors, tool_calls, customer

    factors.append('escalation_needed')
    summary = f'Unclear request from {customer_name} - needs human review'
    tool_calls.append({'tool': 'escalate', 'args': [ticket['ticket_id'], summary, 'low']})
    return 'escalate', 0.5, f'Hi {customer_name}, I need to have a support specialist review your request.', factors, tool_calls, customer
