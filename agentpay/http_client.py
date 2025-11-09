"""
HTTP Client for AgentPay SDK
Handles communication with remote AgentPay backend API
"""

import requests
from typing import Dict, Any, Optional
from datetime import datetime


class HTTPClient:
    """
    HTTP client for communicating with AgentPay backend API.

    Handles authentication, request formatting, and response parsing.
    """

    def __init__(self, api_key: str, base_url: str = "http://localhost:5001"):
        """
        Initialize HTTP client with API key authentication.

        Args:
            api_key: API key for authentication (sk_test_xxx or sk_live_xxx)
            base_url: Base URL of the AgentPay API (default: http://localhost:5001)
        """
        if not api_key:
            raise ValueError("API key is required")

        if not api_key.startswith('sk_'):
            raise ValueError("Invalid API key format. Must start with 'sk_test_' or 'sk_live_'")

        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

        # Set default headers
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'AgentPay-SDK/1.0'
        })

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., '/api/sdk/agents')
            data: Request body data (for POST/PUT)
            params: Query parameters (for GET)

        Returns:
            Response data as dictionary

        Raises:
            requests.HTTPError: If request fails
            ValueError: If response format is invalid
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=30
            )

            # Raise exception for HTTP errors
            response.raise_for_status()

            # Parse JSON response
            return response.json()

        except requests.exceptions.HTTPError as e:
            # Try to extract error message from response
            try:
                error_data = e.response.json()
                error_msg = error_data.get('error', str(e))
                message = error_data.get('message', '')
                raise requests.HTTPError(
                    f"{error_msg}: {message}" if message else error_msg,
                    response=e.response
                )
            except (ValueError, AttributeError):
                raise e

        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request to {url} timed out")

        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Failed to connect to {url}. Is the server running?")

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request."""
        return self._make_request('GET', endpoint, params=params)

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a POST request."""
        return self._make_request('POST', endpoint, data=data)

    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a PUT request."""
        return self._make_request('PUT', endpoint, data=data)

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make a DELETE request."""
        return self._make_request('DELETE', endpoint)

    def ping(self) -> Dict[str, Any]:
        """
        Test API connection and authentication.

        Returns:
            Dict with success status and authenticated user info

        Raises:
            Exception if authentication fails
        """
        return self.get('/api/sdk/ping')

    # ========== Virtual Card Methods ==========

    def request_payment_card(
        self,
        amount: int,
        purpose: str,
        justification: str,
        agent_id: str = "sdk-agent",
        expected_roi: Optional[str] = None,
        urgency: str = "Medium",
        budget_remaining: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Request a virtual card with quorum approval.

        Args:
            amount: Amount limit for the card (in cents)
            purpose: What the card will be used for
            justification: Detailed explanation for the request
            agent_id: ID of the requesting agent (default: "sdk-agent")
            expected_roi: Expected return on investment
            urgency: Request urgency - "Low", "Medium", or "High"
            budget_remaining: Optional remaining budget context

        Returns:
            Dict with approval result and card details if approved

        Example:
            ```python
            result = client.request_payment_card(
                amount=10000,  # $100
                purpose="OpenAI API Credits",
                justification="Need GPT-4 for customer support chatbot",
                expected_roi="Save $3,000/month in support costs",
                urgency="High"
            )

            if result['approved']:
                card = result['card']
                print(f"Card: {card['card_number']}")
            else:
                print(f"Denied: {result['denial_reason']}")
            ```
        """
        data = {
            'amount': amount,
            'purpose': purpose,
            'justification': justification,
            'agent_id': agent_id,
            'expected_roi': expected_roi,
            'urgency': urgency,
            'budget_remaining': budget_remaining
        }

        return self.post('/api/sdk/cards/request', data=data)

    def get_card_details(self, card_id: str) -> Dict[str, Any]:
        """
        Get details of a virtual card.

        Args:
            card_id: ID of the card

        Returns:
            Dict with card details

        Example:
            ```python
            card = client.get_card_details("card-123")
            print(f"Status: {card['status']}")
            print(f"Expires: {card['expires_at']}")
            ```
        """
        response = self.get(f'/api/sdk/cards/{card_id}')
        return response.get('card')

    def cancel_card(self, card_id: str) -> bool:
        """
        Cancel a virtual card.

        Args:
            card_id: ID of the card to cancel

        Returns:
            True if successful

        Example:
            ```python
            success = client.cancel_card("card-123")
            if success:
                print("Card cancelled")
            ```
        """
        response = self.post(f'/api/sdk/cards/{card_id}/cancel')
        return response.get('success', False)

    def charge_card(
        self,
        card_number: str,
        cvv: str,
        expiry_date: str,
        amount: int,
        merchant_name: str
    ) -> Dict[str, Any]:
        """
        Attempt to charge a virtual card (mock merchant).

        Args:
            card_number: 16-digit card number
            cvv: 3-digit CVV
            expiry_date: Expiry date in MM/YY format
            amount: Amount to charge (in cents)
            merchant_name: Name of the merchant

        Returns:
            Dict with charge result

        Example:
            ```python
            result = client.charge_card(
                card_number="4242424242424242",
                cvv="123",
                expiry_date="12/25",
                amount=10000,
                merchant_name="OpenAI API Credits"
            )

            if result['success']:
                print(f"Charge successful: {result['transaction_id']}")
            else:
                print(f"Charge failed: {result['error']}")
            ```
        """
        data = {
            'card_number': card_number,
            'cvv': cvv,
            'expiry_date': expiry_date,
            'amount': amount,
            'merchant_name': merchant_name
        }

        return self.post('/api/mock-merchant/charge', data=data)

    def close(self):
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()
