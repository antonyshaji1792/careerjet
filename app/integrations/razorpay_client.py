import razorpay
import os
import logging
from flask import current_app

logger = logging.getLogger(__name__)

class RazorpayClient:
    """
    Centralized Razorpay client utility for CareerJet.
    Handles client initialization and provides consistent error handling.
    """
    
    _client = None

    @classmethod
    def get_client(cls):
        """
        Initializes and returns the Razorpay client.
        Ensures credentials are loaded from environment variables.
        """
        if cls._client is None:
            key_id = os.getenv('RAZORPAY_KEY_ID')
            key_secret = os.getenv('RAZORPAY_KEY_SECRET')

            if not key_id or not key_secret:
                logger.error("Razorpay credentials missing in environment variables.")
                raise ValueError("RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET not found.")

            try:
                cls._client = razorpay.Client(auth=(key_id, key_secret))
                # Optional: log a message indicating which mode is active (sandbox vs live)
                # Razorpay keys usually start with 'rzp_test_' for sandbox
                mode = "SANDBOX" if key_id.startswith('rzp_test_') else "LIVE"
                logger.info(f"Razorpay client initialized in {mode} mode.")
            except Exception as e:
                logger.error(f"Failed to initialize Razorpay client: {str(e)}")
                raise

        return cls._client

    @staticmethod
    def verify_webhook_signature(payload, signature):
        """
        Verifies the Razorpay webhook signature.
        """
        webhook_secret = os.getenv('RAZORPAY_WEBHOOK_SECRET')
        if not webhook_secret:
            logger.error("RAZORPAY_WEBHOOK_SECRET not configured.")
            return False

        client = RazorpayClient.get_client()
        try:
            # Razorpay SDK method for signature verification
            client.utility.verify_webhook_signature(payload, signature, webhook_secret)
            return True
        except razorpay.errors.SignatureVerificationError:
            logger.warning("Razorpay webhook signature verification failed.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Razorpay webhook verification: {str(e)}")
            return False
