import json
from urllib.parse import urlparse

from flask import current_app
from pywebpush import WebPushException, webpush

from models import NotificationSubscription

vapid_public_key = "[PUBLIC_KEY]"
vapid_private_key = "[PRIVATE_KEY]"
vapid_claims = {"sub": "https://chaperones.steelcitychoristers.org.uk"}


def send_notification(chaperone_id: int, title: str, message: str, url: str):
    with current_app.app_context():
        subs = NotificationSubscription.query.filter_by(chaperone_id=chaperone_id)
        for sub in subs:
            try:
                subscription_info = json.loads(sub.subscription)
                endpoint = subscription_info.get("endpoint")
                if not endpoint:
                    continue
                parsed = urlparse(endpoint)
                aud = f"{parsed.scheme}://{parsed.netloc}"
                claims = {"sub": "mailto:jamescaroe@gmail.com", "aud": aud}
                webpush(
                    subscription_info=subscription_info,
                    data=json.dumps(
                        {
                            "title": title,
                            "body": message,
                            "url": url,
                        }
                    ),
                    vapid_private_key=vapid_private_key,
                    vapid_claims=claims,  # type: ignore
                )
            except WebPushException as e:
                print("Push error", e)


def broadcast_notification(title: str, message: str):
    with current_app.app_context():
        subs = NotificationSubscription.query.all()
        for sub in subs:
            try:
                subscription_info = json.loads(sub.subscription)
                endpoint = subscription_info.get("endpoint")
                if not endpoint:
                    continue
                parsed = urlparse(endpoint)
                aud = f"{parsed.scheme}://{parsed.netloc}"
                claims = {"sub": "mailto:jamescaroe@gmail.com", "aud": aud}
                webpush(
                    subscription_info=subscription_info,
                    data=json.dumps(
                        {
                            "title": title,
                            "body": message,
                        }
                    ),
                    vapid_private_key=vapid_private_key,
                    vapid_claims=claims,  # type: ignore
                )
            except WebPushException as e:
                print("Push error:", e)
