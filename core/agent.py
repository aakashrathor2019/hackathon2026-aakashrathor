import asyncio, re, json, time, logging
from core import tools
from core.policy import decide
from core.logger import write_log

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def process_ticket(ticket):
    start = time.time()
    try:
        logging.info(f"Processing ticket {ticket['ticket_id']}")

        # Decide action with tool chaining - pass tools module
        action, conf, reason, factors, tool_calls, customer = decide(ticket, tools)

        # Execute tool calls
        executed_tools = []
        for tool_call in tool_calls:
            try:
                tool_name = tool_call['tool']
                args = tool_call['args']
                if tool_name == 'send_reply':
                    result = {'ticket_id': args[0], 'message': args[1]}
                elif tool_name == 'escalate':
                    result = {'ticket_id': args[0], 'summary': args[1], 'priority': args[2]}
                elif tool_name == 'issue_refund':
                    result = {'order_id': args[0], 'amount': args[1]}
                elif tool_name == 'check_refund_eligibility':
                    result = {'order_id': args[0]}
                elif tool_name == 'search_knowledge_base':
                    result = {'query': args[0]}
                elif tool_name == 'get_customer':
                    result = {'email': args[0]}
                elif tool_name == 'get_order':
                    result = {'order_id': args[0]}
                elif tool_name == 'get_product':
                    result = {'product_id': args[0]}
                else:
                    result = {'unknown_tool': tool_name}
                executed_tools.append({tool_name: result})
                logging.info(f"Executed tool: {tool_name}")
            except Exception as e:
                logging.error(f"Tool execution failed: {tool_name} - {e}")
                executed_tools.append({tool_name: {'error': str(e)}})

        # Low confidence fallback
        if conf < 0.6 and action not in ['escalate', 'need_info']:
            action = 'escalate'
            reason += ' (escalated due to low confidence)'
            conf = min(conf, 0.5)

        result = {
            'ticket_id': ticket['ticket_id'],
            'customer': customer['name'] if customer else 'Unknown',
            'action': action,
            'confidence': round(conf, 2),
            'reason': reason,
            'factors': factors,
            'tool_calls': executed_tools,
            'latency_ms': int((time.time() - start) * 1000),
            'processed_at': time.time()
        }

        write_log(result)
        logging.info(f"Ticket {ticket['ticket_id']} processed: {action} (conf: {conf}) - {len(tool_calls)} tools used")

        await asyncio.sleep(0)  # Allow other tasks to run
        return result

    except Exception as e:
        logging.error(f"Error processing ticket {ticket['ticket_id']}: {str(e)}")
        error_result = {
            'ticket_id': ticket['ticket_id'],
            'customer': 'Error',
            'action': 'escalate',
            'confidence': 0.0,
            'reason': f'Processing error: {str(e)}',
            'factors': ['error'],
            'tool_calls': [],
            'latency_ms': int((time.time() - start) * 1000),
            'processed_at': time.time()
        }
        write_log(error_result)
        return error_result

async def process_all_tickets():
    try:
        with open('data/tickets.json') as f:
            tickets = json.load(f)
        logging.info(f"Loaded {len(tickets)} tickets")

        # Process in batches to avoid overwhelming
        batch_size = 5  # Smaller batches for more controlled processing
        results = []
        for i in range(0, len(tickets), batch_size):
            batch = tickets[i:i+batch_size]
            tasks = [process_ticket(t) for t in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            logging.info(f"Processed batch {i//batch_size + 1}")

        return results

    except FileNotFoundError:
        logging.error("tickets.json not found")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in tickets.json: {e}")
        return []