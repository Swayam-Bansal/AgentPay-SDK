"""
Simple test to demonstrate agent-to-agent earning capabilities.
This showcases the NEW features added to AgentPay-SDK.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agentpay import AgentPaySDK


def print_header(title):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"{title:^70}")
    print(f"{'='*70}\n")


def print_section(title):
    """Print a section divider."""
    print(f"\n{'-'*70}")
    print(f"  {title}")
    print(f"{'-'*70}\n")


def main():
    print_header("🎯 AGENT EARNING DEMO - NEW FEATURES")
    
    print("This demo showcases the NEW agent-to-agent earning features:")
    print("  ✅ Agents can receive payments from other agents")
    print("  ✅ Track earnings vs expenses separately")
    print("  ✅ View income transactions (who paid you)")
    print("  ✅ Calculate net profit (earned - spent)")
    print("  ✅ Complete 'Earners' tracking system\n")
    
    # Create SDK in local mode
    sdk = AgentPaySDK()
    
    # ========== SETUP ==========
    print_section("1️⃣  SETUP: Registering Agents")
    
    # Register Agent A (buyer/spender)
    agent_a = sdk.register_agent(
        "agent-a",
        metadata={"name": "Marketing Agent", "role": "buyer"}
    )
    print(f"✅ Registered: {agent_a.display_name} ({agent_a.agent_id})")
    
    # Register Agent B (service provider/earner)
    agent_b = sdk.register_agent(
        "agent-b",
        metadata={"name": "Analytics Agent", "role": "service_provider"}
    )
    print(f"✅ Registered: {agent_b.display_name} ({agent_b.agent_id})")
    
    # Fund Agent A
    print_section("2️⃣  FUNDING: Give Agent A $500")
    sdk.fund_agent("agent-a", 50000)
    balance_a = sdk.get_balance("agent-a")
    print(f"💰 Agent A balance: ${balance_a / 100:.2f}")
    
    # ========== AGENT B EARNS MONEY ==========
    print_section("3️⃣  EARNING: Agent B provides service to Agent A")
    
    print("📋 Service: Data Analysis Report")
    print("💵 Price: $75.00")
    print("👤 Client: Agent A\n")
    
    # Agent A pays Agent B for service
    result = sdk.transfer_to_agent(
        from_agent_id="agent-a",
        to_agent_id="agent-b",
        amount=7500,  # $75
        purpose="Data Analysis Report - Q4 Campaign Metrics"
    )
    
    if result['status'] == 'completed':
        print(f"✅ Payment successful!")
        print(f"   Transaction ID: {result['transaction_id']}")
        print(f"   Amount: ${result['amount'] / 100:.2f}")
        print(f"   From: {result['from_agent']} → To: {result['to_agent']}")
    else:
        print(f"❌ Payment failed: {result.get('error')}")
    
    # ========== CHECK EARNINGS ==========
    print_section("4️⃣  EARNINGS REPORT: Agent B's Income")
    
    earnings = sdk.get_agent_earnings("agent-b")
    
    print(f"💰 Total Earned: ${earnings['total_earned'] / 100:.2f}")
    print(f"📊 Number of Income Transactions: {earnings['transaction_count']}\n")
    
    print("Income Transactions:")
    for txn in earnings['transactions']:
        print(f"  • ${txn['amount'] / 100:.2f} from {txn['from_agent']}")
        print(f"    Purpose: {txn['purpose']}")
        print(f"    Time: {txn['timestamp']}")
        print(f"    Balance after: ${txn['balance_after'] / 100:.2f}\n")
    
    # ========== AGENT B SPENDS SOME MONEY ==========
    print_section("5️⃣  SPENDING: Agent B pays for tools")
    
    # Register a vendor agent (no need to fund them)
    vendor = sdk.register_agent("vendor-c", metadata={"name": "Tool Vendor"})
    
    print("Agent B buys analytics tools for $25\n")
    
    sdk.transfer_to_agent(
        from_agent_id="agent-b",
        to_agent_id="vendor-c",
        amount=2500,  # $25
        purpose="Analytics Software License"
    )
    
    # ========== EXPENSES REPORT ==========
    print_section("6️⃣  EXPENSES REPORT: Agent B's Spending")
    
    expenses = sdk.get_agent_expenses("agent-b")
    
    print(f"💸 Total Spent: ${expenses['total_spent'] / 100:.2f}")
    print(f"📊 Number of Expense Transactions: {expenses['transaction_count']}\n")
    
    print("Expense Transactions:")
    for txn in expenses['transactions']:
        print(f"  • ${abs(txn['amount']) / 100:.2f} to {txn['to_agent']}")
        print(f"    Purpose: {txn['purpose']}")
        print(f"    Time: {txn['timestamp']}")
        print(f"    Balance after: ${txn['balance_after'] / 100:.2f}\n")
    
    # ========== FINAL SUMMARY ==========
    print_section("7️⃣  FINAL SUMMARY: All Agent Balances")
    
    print(f"{'Agent':<20} {'Balance':>12} {'Earned':>12} {'Spent':>12} {'Net Profit':>12}")
    print("-" * 70)
    
    for agent_id in ["agent-a", "agent-b", "vendor-c"]:
        agent = sdk.get_agent(agent_id)
        summary = sdk.get_agent_balance_summary(agent_id)
        
        print(f"{agent.display_name:<20} "
              f"${summary['current_balance']/100:>10.2f}  "
              f"${summary['total_earned']/100:>10.2f}  "
              f"${summary['total_spent']/100:>10.2f}  "
              f"${summary['net_profit']/100:>10.2f}")
    
    print("\n" + "="*70)
    print("KEY INSIGHTS:")
    print("="*70)
    
    summary_b = sdk.get_agent_balance_summary("agent-b")
    
    print(f"\n🎯 Agent B (Analytics Agent):")
    print(f"   • Started with: $0.00")
    print(f"   • Earned from services: ${summary_b['total_earned'] / 100:.2f}")
    print(f"   • Spent on tools: ${summary_b['total_spent'] / 100:.2f}")
    print(f"   • NET PROFIT: ${summary_b['net_profit'] / 100:.2f} ✅")
    print(f"   • Current balance: ${summary_b['current_balance'] / 100:.2f}")
    
    print_header("✅ DEMO COMPLETE - EARNING FEATURES WORKING!")
    
    print("\nNEW SDK Methods Demonstrated:")
    print("  1. sdk.transfer_to_agent() - Agent-to-agent payments")
    print("  2. sdk.get_agent_earnings() - View all income")
    print("  3. sdk.get_agent_expenses() - View all spending")
    print("  4. sdk.get_agent_balance_summary() - Complete financial overview")
    print("\nNEW Model Features:")
    print("  • Agent.total_earned - Lifetime earnings tracker")
    print("  • Agent.total_spent - Lifetime spending tracker")
    print("  • Agent.net_profit - Calculated profit/loss")
    print("  • LedgerEntry.transaction_type - INCOME/EXPENSE categorization")
    print("  • LedgerEntry.counterparty_id - Track who paid/received\n")


if __name__ == "__main__":
    main()
