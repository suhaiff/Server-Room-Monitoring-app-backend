import os
import httpx
import logging

logger = logging.getLogger(__name__)

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "vitabsquare@gmail.com")
SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "vtab")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "vitabsquare@gmail.com")
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


async def send_verification_email(to_email: str, to_name: str, verification_code: str):
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
          <h2 style="color: #333333; text-align: center;">Welcome to VTAB Sentinel!</h2>
          <p style="color: #666666; font-size: 16px;">Hello {to_name},</p>
          <p style="color: #666666; font-size: 16px;">Thank you for registering. Please use the verification code below to complete your setup:</p>
          <div style="text-align: center; margin: 30px 0;">
            <span style="display: inline-block; font-size: 24px; font-weight: bold; background: #0ca5a7; color: #ffffff; padding: 15px 30px; border-radius: 8px; letter-spacing: 5px;">{verification_code}</span>
          </div>
          <p style="color: #666666; font-size: 16px;">This code is valid for a limited time. If you didn't request this, you can safely ignore this email.</p>
          <hr style="border: none; border-top: 1px solid #eeeeee; margin: 30px 0;" />
          <p style="color: #999999; font-size: 12px; text-align: center;">VTAB Sentinel &copy; Enterprise AI Innovation</p>
        </div>
      </body>
    </html>
    """
    
    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": to_email, "name": to_name}],
        "subject": "Your VTAB Sentinel Verification Code",
        "htmlContent": html_content
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(BREVO_URL, headers=headers, json=payload, timeout=10.0)
            if response.status_code >= 400:
                print(f"Brevo API Error: {response.status_code} - {response.text}")
                logger.error(f"Brevo API Error: {response.status_code} - {response.text}")
                return False
            response.raise_for_status()
            print(f"Verification email sent successfully to {to_email}")
            logger.info(f"Verification email sent successfully to {to_email}")
            return True
        except Exception as e:
            print(f"Exception sending email to {to_email}: {str(e)}")
            logger.error(f"Exception sending email to {to_email}: {str(e)}")
            return False

async def send_query_email(message: str, attachment_name: str = None, attachment_b64: str = None) -> bool:
    """Send a support query from the VTab Square page to vitabsquare@gmail.com."""
    if not BREVO_API_KEY:
        logger.error("BREVO_API_KEY is not set. Cannot send query email.")
        return False

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
          <h2 style="color: #0ca5a7;">New Support Query — VTab Sentinel</h2>
          <p style="color: #666; font-size: 15px; border-left: 4px solid #0ca5a7; padding-left: 14px; margin: 20px 0; white-space: pre-wrap;">{message}</p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
          <p style="color: #999; font-size: 12px; text-align: center;">VTab Sentinel &copy; Enterprise AI Innovation</p>
        </div>
      </body>
    </html>
    """

    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": SUPPORT_EMAIL, "name": "VTab Square Support"}],
        "subject": "New Query from VTab Sentinel Support Page",
        "htmlContent": html_content
    }

    if attachment_name and attachment_b64:
        if "," in attachment_b64:
            attachment_b64 = attachment_b64.split(",")[1]
        payload["attachment"] = [{"name": attachment_name, "content": attachment_b64}]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(BREVO_URL, headers=headers, json=payload, timeout=10.0)
            if response.status_code >= 400:
                logger.error(f"Brevo query email error: {response.status_code} - {response.text}")
                return False
            logger.info("Support query email sent successfully.")
            return True
        except Exception as e:
            logger.error(f"Exception sending query email: {str(e)}")
            return False
