"""
PayPal Service for handling PayPal subscriptions and payments.
This service provides a complete interface to PayPal API for subscription management.
"""
import paypalrestsdk
import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse
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
        return bool(
            self.client_id
            and self.client_secret
            and self.client_id != "your-paypal-client-id"
            and self.client_secret != "your-paypal-client-secret"
        )

    def create_billing_plan(
        self,
        plan_code: str,
        plan_name: str,
        description: str,
        amount: float,
        currency: str = "SAR",
        billing_period: str = "monthly",
        app_url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a billing plan in PayPal for a subscription.
        
        Args:
            plan_code: Unique identifier for the plan (e.g., 'basic', 'pro')
            plan_name: Display name of the plan
            description: Description of the plan
            amount: Billing amount in the specified currency
            currency: Currency code (default: SAR)
            billing_period: monthly or yearly
            app_url: Frontend base URL used for PayPal return/cancel callbacks
        
        Returns:
            PayPal plan object if successful, None otherwise
        """
        if not self.is_configured():
            return None

        effective_app_url = (app_url or settings.app_url).rstrip("/")
        is_yearly = billing_period == "yearly"

        # Define the payment definition for the selected billing cycle
        payment_definition = {
            "name": f"{plan_name} - {'Yearly' if is_yearly else 'Monthly'}",
            "type": "REGULAR",
            "frequency": "Year" if is_yearly else "Month",
            "frequency_interval": "1",
            "cycles": "0",  # 0 = infinite (recurring)
            "amount": {
                "currency": currency,
                "value": f"{amount:.2f}"
            }
        }

        # Define merchant preferences
        merchant_preferences = {
            "setup_fee": {
                "currency": currency,
                "value": "0.00"
            },
            "cancel_url": f"{effective_app_url}/settings?billing=cancelled",
            "return_url": f"{effective_app_url}/billing/paypal/execute",
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
            if plan.activate():
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
        start_date = (datetime.now(timezone.utc) + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

        agreement = paypalrestsdk.BillingAgreement({
            "name": "Qentry Platform Subscription",
            "description": "Subscription to Qentry Platform",
            "start_date": start_date,
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

        if agreement.create():
            # Extract the approval URL
            approval_url = None
            for link in agreement.links:
                if link.rel == "approval_url":
                    approval_url = link.href
                    break

            if approval_url:
                token = parse_qs(urlparse(approval_url).query).get("token", [None])[0]
                return {
                    "id": token or agreement.id,
                    "approval_url": approval_url,
                    "token": token,
                    "state": getattr(agreement, "state", None),
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
            return bool(agreement.cancel({"note": "User requested cancellation at period end"}))
        
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
        if not settings.paypal_webhook_id:
            return settings.app_env.lower() != "production"

        required_headers = {
            "paypal-auth-algo",
            "paypal-cert-url",
            "paypal-transmission-id",
            "paypal-transmission-sig",
            "paypal-transmission-time",
        }
        if not required_headers.issubset({k.lower() for k in headers.keys()}):
            return settings.app_env.lower() != "production"

        auth_url = (
            "https://api-m.paypal.com/v1/oauth2/token"
            if self.mode == "live"
            else "https://api-m.sandbox.paypal.com/v1/oauth2/token"
        )
        verify_url = (
            "https://api-m.paypal.com/v1/notifications/verify-webhook-signature"
            if self.mode == "live"
            else "https://api-m.sandbox.paypal.com/v1/notifications/verify-webhook-signature"
        )

        try:
            token_res = requests.post(
                auth_url,
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                timeout=20,
            )
            token_res.raise_for_status()
            access_token = token_res.json()["access_token"]

            verify_res = requests.post(
                verify_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "transmission_id": headers.get("paypal-transmission-id") or headers.get("PayPal-Transmission-Id"),
                    "transmission_time": headers.get("paypal-transmission-time") or headers.get("PayPal-Transmission-Time"),
                    "cert_url": headers.get("paypal-cert-url") or headers.get("PayPal-Cert-Url"),
                    "auth_algo": headers.get("paypal-auth-algo") or headers.get("PayPal-Auth-Algo"),
                    "transmission_sig": headers.get("paypal-transmission-sig") or headers.get("PayPal-Transmission-Sig"),
                    "webhook_id": settings.paypal_webhook_id,
                    "webhook_event": requests.models.complexjson.loads(body),
                },
                timeout=20,
            )
            verify_res.raise_for_status()
            return verify_res.json().get("verification_status") == "SUCCESS"
        except Exception:
            return False


# Singleton instance
_paypal_service: Optional[PayPalService] = None


def get_paypal_service() -> PayPalService:
    """Get or create the PayPal service singleton."""
    global _paypal_service
    if _paypal_service is None:
        _paypal_service = PayPalService()
    return _paypal_service
