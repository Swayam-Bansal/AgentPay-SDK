"""
Autonomous Agent Example - Complete Version
Demonstrates:
1. AI agents requesting payments with quorum consensus (remote mode)
2. Agent-to-agent service payments and earnings tracking (local mode)
3. Complete earning/spending workflow
"""
import os
import sys
import time
from typing import Dict, Optional

# Add parent directory to path to import agentpay
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Try to load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, try to manually load .env
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

from agentpay import AgentPaySDK


class AutonomousMarketingAgent:
    """
    An autonomous agent that can request payments and make purchases.
    
    This agent:
    1. Analyzes business needs (simulated with predefined scenarios)
    2. Requests payment approval with justification
    3. Waits for quorum consensus (5 AI agents vote)
    4. If approved: Uses virtual card to make purchases
    5. Reports results
    """
    
    def __init__(self, api_key: str, agent_id: str = "marketing-agent-001"):
        """
        Initialize the autonomous agent.
        
        Args:
            api_key: AgentPay API key for authentication
            agent_id: Unique identifier for this agent
        """
        self.sdk = AgentPaySDK(api_key=api_key)
        self.agent_id = agent_id
        self.name = "Marketing Agent"
        
        print(f"\n{'='*60}")
        print(f"🤖 {self.name} Initialized")
        print(f"{'='*60}")
        print(f"Agent ID: {agent_id}")
        print(f"SDK Mode: {self.sdk.mode}")
        print(f"{'='*60}\n")
    
    def analyze_and_request_payment(
        self,
        scenario: str = "ad_campaign"
    ) -> Optional[Dict]:
        """
        Analyze business needs and request appropriate payment.
        
        Args:
            scenario: Business scenario to handle
                - "ad_campaign": Request OpenAI credits for ad generation
                - "analytics": Request data tools subscription
                - "infrastructure": Request AWS credits (expensive)
        
        Returns:
            Payment request result with approval status and card details
        """
        
        # Define scenarios with different characteristics
        scenarios = {
            "ad_campaign": {
                "amount": 10000,  # $100
                "purpose": "OpenAI API Credits",
                "justification": (
                    "Need GPT-4 to generate high-quality ad copy for Q4 marketing campaign. "
                    "Current manual copywriting costs $500/week. AI-generated copy has shown "
                    "30% higher engagement in A/B tests."
                ),
                "expected_roi": (
                    "Expected $5,000 in additional revenue from improved ad performance. "
                    "Will save 10 hours/week of copywriter time ($250 value)."
                ),
                "urgency": "High",
                "budget_remaining": 50000
            },
            "analytics": {
                "amount": 5000,  # $50
                "purpose": "Data Analysis Tools Subscription",
                "justification": (
                    "Need advanced analytics platform to track campaign performance metrics. "
                    "Current manual Excel tracking is error-prone and time-consuming."
                ),
                "expected_roi": (
                    "Improved decision-making through real-time data insights. "
                    "Save 5 hours/week of manual data processing."
                ),
                "urgency": "Medium",
                "budget_remaining": 50000
            },
            "infrastructure": {
                "amount": 250000,  # $2,500
                "purpose": "AWS Cloud Services",
                "justification": (
                    "Want to experiment with new cloud infrastructure setup. "
                    "Not urgent, no clear immediate benefit."
                ),
                "expected_roi": "Unclear - exploratory expense",
                "urgency": "Low",
                "budget_remaining": 50000
            }
        }
        
        if scenario not in scenarios:
            print(f"❌ Unknown scenario: {scenario}")
            return None
        
        config = scenarios[scenario]
        
        print(f"\n{'='*60}")
        print(f"📊 SCENARIO: {scenario.upper().replace('_', ' ')}")
        print(f"{'='*60}")
        print(f"Amount Requested: ${config['amount'] / 100:.2f}")
        print(f"Purpose: {config['purpose']}")
        print(f"Urgency: {config['urgency']}")
        print(f"{'='*60}\n")
        
        print("🤖 Agent Decision: Proceeding with payment request...")
        print("📤 Submitting to quorum for approval...\n")
        
        # Request payment card through SDK
        # This triggers the full approval workflow
        try:
            result = self.sdk.request_payment_card(
                amount=config['amount'],
                purpose=config['purpose'],
                justification=config['justification'],
                agent_id=self.agent_id,
                expected_roi=config['expected_roi'],
                urgency=config['urgency'],
                budget_remaining=config['budget_remaining']
            )
            
            print(f"✅ Request processed!")
            print(f"   Approved: {result.get('approved', False)}")
            
            if result.get('approved'):
                print(f"   Card generated: {result.get('card', {}).get('card_number', 'N/A')}")
            else:
                print(f"   Denial reason: {result.get('denial_reason', 'Unknown')}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error requesting payment: {e}\n")
            return None
    
    def make_purchase(
        self,
        card: Dict,
        merchant: str = "OpenAI API Credits"
    ) -> bool:
        """
        Attempt to make a purchase using the virtual card.
        
        Args:
            card: Card details from approval result
            merchant: Merchant name
        
        Returns:
            True if purchase successful, False otherwise
        """
        
        print(f"\n{'='*60}")
        print(f"💳 ATTEMPTING PURCHASE")
        print(f"{'='*60}")
        print(f"Merchant: {merchant}")
        print(f"Amount: ${card.get('amount_limit', 0) / 100:.2f}")
        print(f"{'='*60}\n")
        
        try:
            result = self.sdk.charge_card(
                card_number=card['card_number'],
                cvv=card['cvv'],
                expiry_date=card['expiry_date'],
                amount=card['amount_limit'],
                merchant_name=merchant
            )
            
            if result.get('success'):
                print(f"✅ PURCHASE SUCCESSFUL!")
                print(f"   Transaction ID: {result.get('transaction_id')}")
                return True
            else:
                print(f"❌ PURCHASE FAILED: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"❌ Error making purchase: {e}\n")
            return False
    
    def run_scenario(self, scenario: str) -> Dict:
        """
        Run a complete autonomous workflow for a given scenario.
        
        Args:
            scenario: The business scenario to execute
        
        Returns:
            Summary of the workflow execution
        """
        
        print(f"\n{'#'*60}")
        print(f"# AUTONOMOUS AGENT WORKFLOW: {scenario.upper()}")
        print(f"{'#'*60}\n")
        
        start_time = time.time()
        
        # Step 1: Request payment approval
        approval_result = self.analyze_and_request_payment(scenario)
        
        if not approval_result:
            return {
                'scenario': scenario,
                'approved': False,
                'purchased': False,
                'transaction_id': None,
                'duration': time.time() - start_time
            }
        
        approved = approval_result.get('approved', False)
        
        # Step 2: If approved, make purchase
        purchased = False
        if approved:
            card = approval_result.get('card')
            if card:
                purchased = self.make_purchase(card)
        
        duration = time.time() - start_time
        
        summary = {
            'scenario': scenario,
            'approved': approved,
            'purchased': purchased,
            'transaction_id': approval_result.get('transaction_id'),
            'duration': duration
        }
        
        print(f"\n{'='*60}")
        print("📊 WORKFLOW SUMMARY")
        print(f"{'='*60}")
        print(f"Scenario: {scenario}")
        print(f"Approved: {'✅ Yes' if approved else '❌ No'}")
        print(f"Purchased: {'✅ Yes' if purchased else '❌ No'}")
        print(f"Duration: {duration:.2f}s")
        print(f"{'='*60}\n")
        
        return summary


class AutonomousServiceAgent:
    """
    An autonomous agent that can both SPEND and EARN money.
    
    This agent:
    - Provides services to other agents
    - Receives payments for services rendered
    - Tracks earnings and income history
    - Manages profit/loss from operations
    """
    
    def __init__(self, sdk: AgentPaySDK, agent_id: str = "service-agent-001", service_type: str = "Analytics"):
        """
        Initialize the service agent.
        
        Args:
            sdk: AgentPaySDK instance (should be in local mode)
            agent_id: Unique identifier for this agent
            service_type: Type of service this agent provides
        """
        self.sdk = sdk
        self.agent_id = agent_id
        self.name = f"{service_type} Service Agent"
        self.service_type = service_type
        
        print(f"\n{'='*60}")
        print(f"💼 {self.name} Initialized")
        print(f"{'='*60}")
        print(f"Agent ID: {agent_id}")
        print(f"Service: {service_type}")
        print(f"{'='*60}\n")
    
    def provide_service_and_get_paid(
        self,
        client_agent_id: str,
        service_description: str,
        price: int
    ) -> Dict:
        """
        Provide a service to another agent and receive payment.
        
        Args:
            client_agent_id: Agent who is paying for the service
            service_description: What service is being provided
            price: Price in cents
        
        Returns:
            Payment receipt with status
        """
        
        print(f"\n{'='*60}")
        print(f"💼 PROVIDING SERVICE")
        print(f"{'='*60}")
        print(f"Service: {service_description}")
        print(f"Client: {client_agent_id}")
        print(f"Price: ${price / 100:.2f}")
        print(f"{'='*60}\n")
        
        # Simulate service delivery
        print("🔧 Performing service...")
        time.sleep(1)
        print("✅ Service completed!\n")
        
        # Request payment from client agent
        try:
            result = self.sdk.transfer_to_agent(
                from_agent_id=client_agent_id,
                to_agent_id=self.agent_id,
                amount=price,
                purpose=f"Payment for {service_description}"
            )
            
            if result.get('status') == 'completed':
                print(f"💰 PAYMENT RECEIVED!")
                print(f"   Transaction ID: {result['transaction_id']}")
                print(f"   Amount: ${result['amount'] / 100:.2f}")
                print(f"   From: {result['from_agent']}")
                print(f"{'='*60}\n")
                
                # Check updated balance
                summary = self.sdk.get_agent_balance_summary(self.agent_id)
                print(f"📊 UPDATED BALANCE")
                print(f"   Current: ${summary['current_balance'] / 100:.2f}")
                print(f"   Total Earned: ${summary['total_earned'] / 100:.2f}")
                print(f"   Total Spent: ${summary['total_spent'] / 100:.2f}")
                print(f"   Net Profit: ${summary['net_profit'] / 100:.2f}")
                print(f"{'='*60}\n")
                
                return result
            else:
                print(f"❌ PAYMENT FAILED: {result.get('error')}\n")
                return result
        except Exception as e:
            print(f"❌ ERROR: {e}\n")
            return {'status': 'failed', 'error': str(e)}
    
    def view_earnings_report(self):
        """Display a detailed earnings report for this agent."""
        
        print(f"\n{'='*60}")
        print(f"📈 EARNINGS REPORT - {self.name}")
        print(f"{'='*60}\n")
        
        try:
            # Get earnings
            earnings = self.sdk.get_agent_earnings(self.agent_id)
            
            print(f"💰 Total Earned: ${earnings['total_earned'] / 100:.2f}")
            print(f"📊 Transaction Count: {earnings['transaction_count']}\n")
            
            if earnings['transactions']:
                print("Recent Income Transactions:")
                print("-" * 60)
                for txn in earnings['transactions'][:5]:
                    print(f"  • ${txn['amount'] / 100:.2f} from {txn['from_agent']}")
                    print(f"    {txn['purpose']}")
                    print(f"    {txn['timestamp']}")
                    print()
            else:
                print("No income transactions yet.\n")
            
            # Get expenses
            expenses = self.sdk.get_agent_expenses(self.agent_id)
            
            print(f"💸 Total Spent: ${expenses['total_spent'] / 100:.2f}")
            print(f"📊 Transaction Count: {expenses['transaction_count']}\n")
            
            # Get balance summary
            summary = self.sdk.get_agent_balance_summary(self.agent_id)
            
            print("=" * 60)
            print(f"💼 NET PROFIT: ${summary['net_profit'] / 100:.2f}")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Error generating report: {e}\n")
    
    def run_earning_scenario(self, client_agent_id: str, service_price: int = 5000):
        """
        Run a scenario where this agent provides a service and earns money.
        
        Args:
            client_agent_id: Agent who will pay for the service
            service_price: Price for the service (default $50)
        """
        
        print(f"\n{'#'*60}")
        print(f"# EARNING SCENARIO: {self.service_type} Service")
        print(f"{'#'*60}\n")
        
        service_descriptions = {
            "Analytics": "Advanced Campaign Analytics Report",
            "Data": "Data Processing & Cleaning Service",
            "Research": "Market Research Analysis",
            "Content": "Content Generation & Copywriting"
        }
        
        description = service_descriptions.get(self.service_type, f"{self.service_type} Service")
        
        # Provide service and get paid
        payment_result = self.provide_service_and_get_paid(
            client_agent_id=client_agent_id,
            service_description=description,
            price=service_price
        )
        
        # Show earnings report
        if payment_result.get('status') == 'completed':
            self.view_earnings_report()
        
        return payment_result


def main():
    """
    Main function - Run autonomous agent demo with earning capabilities.
    """
    
    print("\n" + "="*60)
    print("🎯 AUTONOMOUS AGENT DEMO - EARNING & SPENDING")
    print("="*60)
    print("\nThis demo shows TWO modes:")
    print("  1. REMOTE MODE: Quorum voting for payment approvals")
    print("  2. LOCAL MODE: Agent-to-agent earning & payments")
    print()
    print("=" * 60 + "\n")
    
    # Get API key from environment or user input
    api_key = os.getenv('AGENTPAY_API_KEY')
    
    if not api_key:
        print("⚠️  No API key found in environment.")
        print("\nChoose a mode:")
        print("  1. REMOTE MODE - Enter API key (tests quorum voting)")
        print("  2. LOCAL MODE  - Press Enter (tests agent earning)")
        choice = input("\nYour choice: ").strip()
        
        if choice and choice != "2":
            api_key = input("Enter your AgentPay API key: ").strip()
    
    # Run appropriate mode
    if api_key:
        print("\n" + "="*60)
        print("🌐 RUNNING IN REMOTE MODE (Quorum Voting)")
        print("="*60 + "\n")
        
        agent = AutonomousMarketingAgent(api_key=api_key)
        
        scenarios = [
            ("ad_campaign", "Should APPROVE - Good ROI, high urgency"),
            ("analytics", "Should APPROVE - Clear value, medium urgency"),
        ]
        
        results = []
        
        for i, (scenario, description) in enumerate(scenarios, 1):
            print(f"\n{'#'*60}")
            print(f"# SCENARIO {i}/{len(scenarios)}: {description}")
            print(f"{'#'*60}\n")
            
            result = agent.run_scenario(scenario)
            results.append(result)
            
            if i < len(scenarios):
                time.sleep(2)
        
        # Summary
        print(f"\n\n{'#'*60}")
        print("# REMOTE MODE SUMMARY")
        print(f"{'#'*60}\n")
        
        for i, result in enumerate(results, 1):
            status = "✅ SUCCESS" if result['purchased'] else ("⏸️  DENIED" if not result['approved'] else "❌ FAILED")
            print(f"{i}. {result['scenario'].upper()}: {status}")
        
        print(f"{'#'*60}\n")
    
    else:
        print("\n" + "="*60)
        print("🏠 RUNNING IN LOCAL MODE (Agent-to-Agent Earning)")
        print("="*60 + "\n")
        
        # Create SDK in local mode
        sdk = AgentPaySDK()
        
        # Register two agents
        print("📝 Registering agents...")
        marketing_agent = sdk.register_agent(
            "marketing-agent-001",
            metadata={"name": "Marketing Agent", "role": "marketing"}
        )
        service_agent = sdk.register_agent(
            "analytics-agent-002", 
            metadata={"name": "Analytics Agent", "role": "service_provider"}
        )
        
        # Fund the marketing agent (they'll pay for services)
        print("💰 Funding marketing agent with $500...\n")
        sdk.fund_agent("marketing-agent-001", 50000)  # $500
        
        # Create service agent wrapper
        analytics_agent = AutonomousServiceAgent(
            sdk=sdk,
            agent_id="analytics-agent-002",
            service_type="Analytics"
        )
        
        # Run earning scenario
        print(f"\n{'#'*60}")
        print("# SCENARIO: Agent Provides Service & Earns Money")
        print(f"{'#'*60}\n")
        
        analytics_agent.run_earning_scenario(
            client_agent_id="marketing-agent-001",
            service_price=7500  # $75
        )
        
        # Show final balances for both agents
        print(f"\n{'='*60}")
        print("📊 FINAL AGENT BALANCES")
        print(f"{'='*60}\n")
        
        for agent_id in ["marketing-agent-001", "analytics-agent-002"]:
            agent = sdk.get_agent(agent_id)
            summary = sdk.get_agent_balance_summary(agent_id)
            
            print(f"{agent.display_name} ({agent_id})")
            print(f"  Balance: ${summary['current_balance'] / 100:.2f}")
            print(f"  Earned: ${summary['total_earned'] / 100:.2f}")
            print(f"  Spent: ${summary['total_spent'] / 100:.2f}")
            print(f"  Net Profit: ${summary['net_profit'] / 100:.2f}")
            print()
        
        print("="*60)
        print("✅ LOCAL MODE DEMO COMPLETE")
        print("="*60 + "\n")


if __name__ == "__main__":
    main()
