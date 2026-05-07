import os

# Sends emails either in development mode or production mode.
def send_email(to_email: str, subject: str, html: str, to_name: str = ""):
    """
    Dev mode: if MAIL_ENABLED=false, print to terminal instead of sending.
    Prod mode: if MAIL_ENABLED=true, send via Mailjet.
    """

    # Checks whether real email sending is enabled.
    mail_enabled = os.getenv("MAIL_ENABLED", "false").lower() == "true"

    # Development mode:
    # Instead of sending emails, prints the email content to the terminal.
    if not mail_enabled:

        print("\n" + "=" * 70)
        print("DEV EMAIL (NOT SENT)")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print("HTML:")
        print(html)
        print("=" * 70 + "\n")

        return {"dev_mode": True, "sent": False}

    # Production mode:
    # Sends emails using the Mailjet API.
    from mailjet_rest import Client

    # Gets Mailjet API credentials from environment variables.
    api_key = os.getenv("MAILJET_API_KEY")
    api_secret = os.getenv("MAILJET_API_SECRET")

    # Prevents the app from running without valid Mailjet credentials.
    if not api_key or not api_secret:
        raise RuntimeError("MAILJET_API_KEY / MAILJET_API_SECRET missing in environment")

    # Default sender information.
    from_email = os.getenv("MAIL_FROM_EMAIL", "noreply@spendsenseapp.com")
    from_name = os.getenv("MAIL_FROM_NAME", "SpendSense")

    # Creates the Mailjet API client.
    mailjet = Client(auth=(api_key, api_secret), version="v3.1")

    # Email payload sent to Mailjet.
    data = {
        "Messages": [
            {
                "From": {"Email": from_email, "Name": from_name},

                # Uses the provided recipient name if available.
                "To": [{"Email": to_email, "Name": to_name or to_email}],

                "Subject": subject,
                "HTMLPart": html,
            }
        ]
    }

    # Sends the email request to Mailjet.
    res = mailjet.send.create(data=data)

    # Raises an error if Mailjet fails to send the email.
    if res.status_code not in (200, 201):
        raise RuntimeError(f"Mailjet error {res.status_code}: {res.json()}")

    return res.json()