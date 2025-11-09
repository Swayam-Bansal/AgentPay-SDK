"""
Autonomous Agent Example - Dedalus-Style
Demonstrates an AI agent that can autonomously request payments,
get approval via quorum consensus, and make purchases.

Also demonstrates agent-to-agent service payments and earnings tracking.
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
                    os.environ[key.strip()] = value.strip()

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
            
            print(f"\n{'='*60}")
            print("📋 QUORUM CONSENSUS RESULT")
            print(f"{'='*60}")
            
            if result.get('approved'):
                print("✅ STATUS: APPROVED")
                
                consensus = result.get('consensus_result', {})
                print(f"\nVotes: {consensus.get('yes_votes', 0)} YES, "
                      f"{consensus.get('no_votes', 0)} NO, "
                      f"{consensus.get('abstain_votes', 0)} ABSTAIN")
                print(f"Risk Score: {consensus.get('average_risk_score', 0):.2f}/10")
                
                card = result.get('card', {})
                print(f"\n💳 VIRTUAL CARD GENERATED:")
                print(f"   Card Number: {card.get('card_number', 'N/A')}")
                print(f"   CVV: {card.get('cvv', 'N/A')}")
                print(f"   Expiry: {card.get('expiry_date', 'N/A')}")
                print(f"   Limit: ${card.get('amount_limit', 0) / 100:.2f}")
                print(f"   Expires At: {card.get('expires_at', 'N/A')}")
                print(f"   Status: {card.get('status', 'N/A')}")
                
            else:
                print("❌ STATUS: DENIED")
                
                consensus = result.get('consensus_result', {})
                print(f"\nVotes: {consensus.get('yes_votes', 0)} YES, "
                      f"{consensus.get('no_votes', 0)} NO, "
                      f"{consensus.get('abstain_votes', 0)} ABSTAIN")
                
                denial_reason = result.get('denial_reason', 'No reason provided')
                print(f"\n🚫 Denial Reasoning:")
                print(f"   {denial_reason}")
            
            print(f"\nTransaction ID: {result.get('transaction_id', 'N/A')}")
            print(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
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
                print("✅ PURCHASE SUCCESSFUL!")
                print(f"   Transaction ID: {result.get('transaction_id')}")
                print(f"   Merchant: {result.get('merchant')}")
                print(f"   Amount: ${result.get('amount', 0) / 100:.2f}")
                print(f"   Card (last 4): ****{result.get('card_last_4')}")
                print(f"{'='*60}\n")
                return True
            else:
                print("❌ PURCHASE FAILED!")
                print(f"   Error: {result.get('error')}")
                print(f"{'='*60}\n")
                return False
                
        except Exception as e:
            print(f"❌ PURCHASE ERROR: {e}")
            import traceback
            traceback.print_exc()
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
                'error': 'Failed to get approval result',
                'duration': time.time() - start_time
            }
        
        approved = approval_result.get('approved', False)
        
        # Step 2: If approved, make purchase
        purchased = False
        if approved:
            card = approval_result.get('card')
            if card:
                purchased = self.make_purchase(
                    card,
                    merchant=card.get('purpose', 'OpenAI API Credits')
                )
        
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


def main():
    """
    Main function - Run autonomous agent demo.
    """
    
    # Get API key from environment or user input
    api_key = os.getenv('AGENTPAY_API_KEY')
    
    if not api_key:
        print("\n⚠️  No API key found in environment.")
        print("Please set AGENTPAY_API_KEY environment variable or enter it below.")
        api_key = input("\nEnter your AgentPay API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Exiting.")
        return
    
    # Initialize autonomous agent
    agent = AutonomousMarketingAgent(api_key=api_key)
    
    # Run different scenarios
    print("\n" + "="*60)
    print("🎯 RUNNING 3 AUTONOMOUS AGENT SCENARIOS")
    print("="*60 + "\n")
    
    scenarios = [
        ("ad_campaign", "Should APPROVE - Good ROI, high urgency"),
        ("analytics", "Should APPROVE - Clear value, medium urgency"),
        ("infrastructure", "Should DENY - Vague ROI, low urgency, too expensive")
    ]
    
    results = []
    
    for i, (scenario, description) in enumerate(scenarios, 1):
        print(f"\n{'#'*60}")
        print(f"# SCENARIO {i}/3: {description}")
        print(f"{'#'*60}\n")
        
        result = agent.run_scenario(scenario)
        results.append(result)
        
        # Wait between scenarios
        if i < len(scenarios):
            print("\n⏳ Waiting 5 seconds before next scenario...\n")
            time.sleep(5)
    
    # Final summary
    print(f"\n\n{'#'*60}")
    print("# FINAL SUMMARY - ALL SCENARIOS")
    print(f"{'#'*60}\n")
    
    for i, result in enumerate(results, 1):
        status = "✅ SUCCESS" if result['purchased'] else ("⏸️  DENIED" if not result['approved'] else "❌ FAILED")
        print(f"{i}. {result['scenario'].upper()}: {status}")
        print(f"   Approved: {result['approved']}, Purchased: {result['purchased']}")
        print(f"   Duration: {result['duration']:.2f}s")
        print()
    
    print(f"{'#'*60}\n")


if __name__ == "__main__":
    main()
