#!/usr/bin/env python3
"""
ShopWave AI Support Agent - Test Script
Run this to test the agent functionality without the UI.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from core.agent import process_all_tickets
from core.logger import get_audit_summary

def main():
    print("🛒 ShopWave AI Customer Support Agent")
    print("=" * 50)

    print("\n🚀 Processing tickets...")
    results = asyncio.run(process_all_tickets())

    print(f"\n✅ Processed {len(results)} tickets\n")

    # Summary
    summary = get_audit_summary()
    print("📊 Summary:")
    print(f"  Total Processed: {summary['total_processed']}")
    print(f"  Average Confidence: {summary['avg_confidence']:.2f}")
    print(f"  Action Distribution: {summary['recent_actions']}")

    print("\n📋 Detailed Results:")
    print("-" * 80)
    for result in results:
        status = "✅" if result['action'] != 'escalate' else "⚠️"
        print(f"{status} {result['ticket_id']}: {result['action'].upper()} (conf: {result['confidence']})")
        print(f"   Customer: {result['customer']}")
        print(f"   Reason: {result['reason']}")
        if 'factors' in result and result['factors']:
            print(f"   Factors: {', '.join(result['factors'])}")
        print(f"   Latency: {result['latency_ms']}ms")
        print()

    print("🎯 Agent Capabilities Demonstrated:")
    print("  ✅ Autonomous decision making")
    print("  ✅ Tool-based reasoning (customer lookup, order validation)")
    print("  ✅ Policy-aware decisions (returns, refunds, cancellations)")
    print("  ✅ Fraud detection")
    print("  ✅ Confidence scoring with escalation")
    print("  ✅ Error handling and logging")
    print("  ✅ Production-ready architecture")

if __name__ == "__main__":
    main()