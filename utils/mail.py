import logging
from smtplib import SMTP_SSL as SMTP

import resend

SMTPserver = "send.one.com"
sender = "chaperones@steelcitychoristers.org.uk"

USERNAME = "chaperones@steelcitychoristers.org.uk"
PASSWORD = "[PASSWORD]"

API_KEY = "[API_KEY]"
resend.api_key = API_KEY

mail_logger = logging.getLogger("app_logger")
mail_logger.setLevel(logging.INFO)

# Create console handler and set level to info
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter and add it to the handler
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

# Add the handler to the logger
mail_logger.addHandler(console_handler)


def send_mail(destination, subject, html) -> bool:
    try:
        resend.Emails.send(
            {
                "from": "chaperones@steelcitychoristers.org.uk",
                "to": destination,
                "subject": subject,
                "html": html,
            }
        )
        return True
    except Exception:
        return False


def send_mail_many(mails: list):
    conn = SMTP(SMTPserver)
    conn.set_debuglevel(False)
    conn.login(USERNAME, PASSWORD)

    for mail in mails:
        conn.sendmail(sender, mail[0], mail[1], mail[2])

    conn.quit()
