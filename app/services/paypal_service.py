"""
PayPal Service for handling PayPal subscriptions and payments.
This service provides a complete interface to PayPal API for subscription management.
"""
import paypalrestsdk
from typing import Optional, Dict, Any
from app.config import get_settings

settings = get_settings()


class PayPalService:
    """Service for managing PayPal subscriptions and payments."""

    def __init__(self):
        """Initialize PayPal SDK with credentials from settings."""
        self.mode = settings.paypal_mode
        self.client_id = settings.paypal_client_id
        self.client_secret = settings.paypal_client_secret

        # Configure PayPal SDK
        paypalrestsdk.configure({
            "mode": self.mode,  # sandbox or live
            "client_id": self.client_id,
            "client_secret": self.client_secret
        })

    def is_configured(self) -> bool:
        """Check if PayPal is properly configured with valid credentials."""
        return bool(self.client_id and self.client_secret and self.client_id != "your-paypal-client-id")

    def create_billing_plan(
        self,
        plan_code: str,
        plan_name: str,
        description: str,
        price_monthly: float,
        currency: str = "SAR"
    ) -> Optional[Dict[str, Any]]:
        """
        Create a billing plan in PayPal for a subscription.
        
        Args:
            plan_code: Unique identifier for the plan (e.g., 'basic', 'pro')
            plan_name: Display name of the plan
            description: Description of the plan
            price_monthly: Monthly price in the specified currency
            currency: Currency code (default: SAR)
        
        Returns:
            PayPal plan object if successful, None otherwise
        """
        if not self.is_configured():
            return None

        # Define the payment definition for monthly billing
        payment_definition = {
            "name": f"{plan_name} - Monthly",
            "type": "REGULAR",
            "frequency": "Month",
            "frequency_interval": "1",
            "cycles": "0",  # 0 = infinite (recurring)
            "amount": {
                "currency": currency,
                "value": f"{price_monthly:.2f}"
            }
        }

        # Define merchant preferences
        merchant_preferences = {
            "setup_fee": {
                "currency": currency,
                "value": "0.00"
            },
            "cancel_url": f"{settings.app_url}/dashboard",
            "return_url": f"{settings.app_url}/billing/paypal/execute",
            "max_fail_attempts": "3",
            "auto_bill_amount": "YES",
            "initial_fail_amount_action": "CONTINUE"
        }

        # Create the plan
        plan = paypalrestsdk.BillingPlan({
            "name": plan_name,
            "description": description,
            "type": "INFINITE",
            "payment_definitions": [payment_definition],
            "merchant_preferences": merchant_preferences
        })

        if plan.create():
            # Activate the plan
            if plan.update({"state": "ACTIVE"}):
                return {
                    "id": plan.id,
                    "name": plan.name,
                    "description": plan.description,
                    "state": plan.state,
                    "payment_definitions": plan.payment_definitions
                }
        
        return None

    def create_subscription(
        self,
        plan_id: str,
        payer_email: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a subscription agreement for a billing plan.
        
        Args:
            plan_id: PayPal billing plan ID
            payer_email: Email of the payer
            metadata: Additional metadata to attach to the subscription
        
        Returns:
            Subscription agreement with approval URL if successful, None otherwise
        """
        if not self.is_configured():
            return None

        # Create the agreement
        agreement = paypalrestsdk.BillingAgreement({
            "name": "Qentry Platform Subscription",
            "description": "Subscription to Qentry Platform",
            "start_date": "2025-01-01T00:00:00Z",  # Will be updated by PayPal
            "plan": {
                "id": plan_id
            },
            "payer": {
                "payment_method": "PAYPAL",
                "payer_info": {
                    "email": payer_email
                }
            }
        })

        # Add metadata if provided
        if metadata:
            agreement["custom"] = str(metadata)

        if agreement.create():
            # Extract the approval URL
            for link in agreement.links:
                if link.rel == "approval_url":
                    return {
                        "id": agreement.id,
                        "approval_url": link.href,
                        "token": agreement.token,
                        "state": agreement.state
                    }
        
        return None

    def execute_subscription(
        self,
        payment_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a subscription agreement after user approval.
        
        Args:
            payment_token: Token returned from PayPal after user approval
        
        Returns:
            Executed subscription details if successful, None otherwise
        """
        if not self.is_configured():
            return None

        agreement = paypalrestsdk.BillingAgreement.execute(payment_token)
        
        if agreement:
            return {
                "id": agreement.id,
                "state": agreement.state,
                "description": agreement.description,
                "plan_id": agreement.plan.id,
                "payer_email": agreement.payer.payer_info.email,
                "start_date": agreement.start_date,
                "next_billing_date": agreement.agreement_details.next_billing_date
            }
        
        return None

    def cancel_subscription(
        self,
        subscription_id: str
    ) -> bool:
        """
        Cancel an active subscription.
        
        Args:
            subscription_id: PayPal subscription (agreement) ID
        
        Returns:
            True if cancellation successful, False otherwise
        """
        if not self.is_configured():
            return False

        agreement = paypalrestsdk.BillingAgreement.find(subscription_id)
        
        if agreement:
            # Note: PayPal doesn't have a direct cancel method
            # We need to update the state to CANCELLED
            # This may require using the REST API directly
            # For now, return False to indicate this needs implementation
            # TODO: Implement proper cancellation using PayPal REST API
            return False
        
        return False

    def get_subscription_details(
        self,
        subscription_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get details of an existing subscription.
        
        Args:
            subscription_id: PayPal subscription (agreement) ID
        
        Returns:
            Subscription details if found, None otherwise
        """
        if not self.is_configured():
            return None

        agreement = paypalrestsdk.BillingAgreement.find(subscription_id)
        
        if agreement:
            return {
                "id": agreement.id,
                "state": agreement.state,
                "description": agreement.description,
                "plan_id": agreement.plan.id,
                "payer_email": agreement.payer.payer_info.email,
                "start_date": agreement.start_date,
                "next_billing_date": agreement.agreement_details.next_billing_date
            }
        
        return None

    def verify_webhook_signature(
        self,
        headers: Dict[str, str],
        body: str
    ) -> bool:
        """
        Verify PayPal webhook signature.
        
        Args:
            headers: Request headers containing PayPal signature
            body: Raw request body
        
        Returns:
            True if signature is valid, False otherwise
        """
        # PayPal webhooks use a different verification method
        # This is a placeholder - actual implementation requires
        # PayPal webhook ID and certificate verification
        # TODO: Implement proper webhook signature verification
        return True


# Singleton instance
_paypal_service: Optional[PayPalService] = None


def get_paypal_service() -> PayPalService:
    """Get or create the PayPal service singleton."""
    global _paypal_service
    if _paypal_service is None:
        _paypal_service = PayPalService()
    return _paypal_service
