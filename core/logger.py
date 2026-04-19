import json, logging
from pathlib import Path
from datetime import datetime

LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)

AUDIT_LOG = LOG_DIR / 'audit.log'
AUDIT_JSON = Path('audit_log.json')
ERROR_LOG = LOG_DIR / 'error.log'
DEAD_LETTER_LOG = LOG_DIR / 'dead_letter.log'

# Set up file handlers
audit_handler = logging.FileHandler(AUDIT_LOG)
audit_handler.setLevel(logging.INFO)
audit_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

error_handler = logging.FileHandler(ERROR_LOG)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger('shopwave_agent')
logger.addHandler(audit_handler)
logger.addHandler(error_handler)

def write_log(obj):
    """Write structured audit log as JSON array"""
    try:
        audit_file = AUDIT_JSON
        if audit_file.exists():
            with open(audit_file, 'r') as f:
                data = json.load(f)
        else:
            data = []
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            **obj
        }
        data.append(log_entry)
        
        with open(audit_file, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")

def log_error(ticket_id, error):
    """Log processing errors"""
    logger.error(f"Ticket {ticket_id}: {error}")


def log_dead_letter(ticket_id, issue):
    """Log tickets that could not be resolved after retries"""
    try:
        with open(DEAD_LETTER_LOG, 'a') as f:
            f.write(json.dumps({'ticket_id': ticket_id, 'issue': issue, 'timestamp': datetime.now().isoformat()}) + '\n')
    except Exception as e:
        logger.error(f"Failed to write dead letter log: {e}")


def get_audit_summary():
    """Get summary of processed tickets"""
    try:
        with open(AUDIT_LOG, 'r') as f:
            lines = f.readlines()
        actions = {}
        total = len(lines)
        for line in lines[-100:]:  # Last 100 entries
            try:
                entry = json.loads(line)
                action = entry.get('action', 'unknown')
                actions[action] = actions.get(action, 0) + 1
            except:
                pass
        return {
            'total_processed': total,
            'recent_actions': actions,
            'avg_confidence': sum(float(json.loads(line).get('confidence', 0)) for line in lines[-100:]) / max(len(lines[-100:]), 1)
        }
    except FileNotFoundError:
        return {'total_processed': 0, 'recent_actions': {}, 'avg_confidence': 0.0}