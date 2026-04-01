from functools import wraps

import bcrypt
import requests
from flask import g, jsonify, request

from models import *

CLIENT_ID = "[CLIENT_ID]"
CLIENT_SECRET = "[CLIENT_SECRET]"
AUDIENCE = "[AUDIENCE]"
REDIRECT_URI = "https://chaperones.steelcitychoristers.org.uk"


def hash_password(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_password


def check_password(password, hashed_password):
    if not (password and hashed_password):
        return False
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user:
            return jsonify({"error": "Unauthorized"}), 401

        if not g.user.is_admin:
            return jsonify({"error": "Forbidden"}), 403

        return f(*args, **kwargs)

    return decorated_function


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("token")
        fingerprint = request.headers.get("fingerprint")
        oAuthToken = request.headers.get("oAuthToken")
        if token and fingerprint:
            access_token = AccessToken.query.filter_by(
                token=token, fingerprint=fingerprint
            ).first()
            if not access_token:
                return jsonify({"error": "Unauthorized"}), 401
            user = Chaperone.query.get(access_token.chaperone_id)
            if not user:
                return jsonify({"error": "User not found"}), 404
            g.user = user

        elif oAuthToken:
            try:
                token_info = verify_access_token(oAuthToken)
                if not token_info:
                    return jsonify({"error": "Unauthorized"}), 401

                audience = (
                    token_info.get("audience") if isinstance(token_info, dict) else None
                )
                if audience != AUDIENCE:
                    revoke_token(oAuthToken)
                    return jsonify({"error": "Invalid audience"}), 401

                email = (
                    token_info.get("email") if isinstance(token_info, dict) else None
                )
                if not email:
                    revoke_token(oAuthToken)
                    return jsonify({"error": "Email not found in token"}), 401

                user = Chaperone.query.filter_by(email=email).first()

                if not user:
                    revoke_token(oAuthToken)
                    return jsonify({"error": "User not found"}), 404

                g.user = user
                # request.user = user # TODO request.user -> g.user

            except Exception as e:
                return jsonify({"error": "Unauthorized"}), 401

        else:
            return jsonify({"error": "Unauthorized"}), 401

        return f(*args, **kwargs)

    return decorated_function


def verify_access_token(access_token):
    response = requests.get(
        f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}"
    )
    data = response.json()

    if "error" in data:
        return jsonify({"error": "Unauthorized"}), 401

    return data


def revoke_token(token):
    response = requests.post(
        "https://oauth2.googleapis.com/revoke",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"token": token},
    )

    if response.status_code != 200:
        print(f"Failed to revoke token: {response.status_code}, {response.text}")
