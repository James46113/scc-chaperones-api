import secrets
from datetime import datetime, timedelta
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import parse_qs, urlparse

import requests
from flask import Blueprint, jsonify, request

from models import *
from utils.security import admin_required, check_password, hash_password, login_required

auth_bp = Blueprint("auth", __name__)

CLIENT_ID = "[CLIENT_ID]"
CLIENT_SECRET = "[CLIENT_SECRET]"
AUDIENCE = "[AUDIENCE]"
REDIRECT_URI = "https://chaperones.steelcitychoristers.org.uk"


# PUBLIC
@auth_bp.route("/forgot_password", methods=["POST"])
def forgot_password():
    try:
        data = request.json

        if not data or "email" not in data or "token" not in data:
            return jsonify({"error": "Invalid Data"}), 400

        email = data["email"]
        user = Chaperone.query.filter_by(email=email).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        tokenURL = data["token"]
        parsed_url = urlparse(tokenURL)
        token = parse_qs(parsed_url.query).get("token", [None])[0]

        user.password_reset_token = token
        user.password_reset_expiry = datetime.now() + timedelta(hours=1)
        db.session.commit()

        destination = [user.email]

        with open("mail_templates/reset_password.html", "r") as f:
            content = f.read()

        content = content.replace("{{reset_link}}", tokenURL)
        content = content.replace("{{name}}", user.name)

        with open("mail_templates/footer.html", "r") as f:
            footer = f.read()

        subject = f"Password Reset - Steel City Choristers"
        html = content + footer

        # with open('mail_templates/Steel-City-Choristers.png', 'rb') as img_file:
        #     img = MIMEImage(img_file.read())
        #     img.add_header('Content-ID', '<logo>')
        #     msg.attach(img)

        from threading import Thread

        from utils.mail import send_mail

        Thread(target=send_mail, args=(destination, subject, html)).start()

        return jsonify({"error": "sent"}), 201

    except KeyError:
        return jsonify({"error": "Invalid Data"}), 400


# PUBLIC
@auth_bp.route("/reset_password", methods=["POST"])
def reset_password():
    data = request.json

    if not data or "new_password" not in data or "token" not in data:
        return jsonify({"error": "Invalid Data"}), 400

    new_password = data["new_password"]
    token = data["token"]
    user = Chaperone.query.filter_by(password_reset_token=token).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    tokens = AccessToken.query.filter_by(chaperone_id=user.id).all()
    for token in tokens:
        db.session.delete(token)

    if user.password_reset_expiry < datetime.now():
        return jsonify({"error": "Token expired"}), 400

    user.password_hash = hash_password(new_password)
    user.password_reset_token = None
    user.password_reset_expiry = None
    db.session.commit()
    return jsonify({"error": ""}), 201


# PUBLIC
@auth_bp.route("/login/token", methods=["POST"])
def login_token():
    data = request.json

    if not data or "token" not in data or "fingerprint" not in data:
        return jsonify({"error": "Invalid Data"}), 400

    accessToken = data["token"]
    fingerprint = data["fingerprint"]

    token = AccessToken.query.filter_by(
        token=accessToken, fingerprint=fingerprint
    ).first()
    if not token:
        return jsonify({"error": "Invalid token"}), 401

    user = Chaperone.query.get(token.chaperone_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.last_login = datetime.now()
    db.session.commit()

    return jsonify({"email": user.email, "is_admin": user.is_admin, "id": user.id}), 200


# PUBLIC
@auth_bp.route("/login/password", methods=["POST"])
def login_password():
    data = request.json

    if (
        not data
        or "email" not in data
        or "password" not in data
        or "fingerprint" not in data
    ):
        return jsonify({"error": "Invalid Data"}), 400

    email = data["email"]
    password = data["password"]
    fingerprint = data["fingerprint"]

    user = Chaperone.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    if not check_password(password, user.password_hash):
        return jsonify({"error": "Incorrect password"}), 401

    user.last_login = datetime.now()

    # Generate a secure access token
    access_token = secrets.token_hex(32)

    # Store the access token in the database
    new_token = AccessToken(
        token=access_token, fingerprint=fingerprint, chaperone_id=user.id
    )  # type: ignore

    db.session.add(new_token)
    db.session.commit()

    # Return the access token in the response
    return jsonify(
        {
            "access_token": access_token,
            "email": user.email,
            "is_admin": user.is_admin,
            "id": user.id,
        }
    ), 200


# PUBLIC
@auth_bp.route("/check_token/<string:token>", methods=["GET"])
def check_token(token):
    user = Chaperone.query.filter_by(password_reset_token=token).first()
    if not user:
        return jsonify({"error": "Token invalid"}), 404

    if user.password_reset_expiry < datetime.now():
        return jsonify({"error": "Token expired"}), 400

    return jsonify({"error": ""}), 200


@auth_bp.route("/login/<string:email>", methods=["GET"])
def login(email):
    user = Chaperone.query.filter_by(email=email).first()
    user.last_login = datetime.now()
    print("set last login")
    db.session.commit()
    if user:
        return jsonify({"is_admin": user.is_admin, "id": user.id}), 200
    else:
        return jsonify({"error": "User not found"}), 403


@auth_bp.route("/token", methods=["POST"])
def get_token():
    data = request.json
    if not data or "code" not in data:
        return jsonify({"error", "Invalid data"}), 400

    code = data.get("code")

    # Make a POST request to Google's OAuth2 token endpoint
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )

    # Parse the response
    data = response.json()
    if "error" in data:
        print(f"Error: {data['error']}")
        return jsonify(data), 400

    # Return the token data
    return jsonify(
        {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "id_token": data.get("id_token"),
            "expires_in": data.get("expires_in"),
        }
    )


@auth_bp.route("/refresh-token", methods=["POST"])
def refresh_token():
    data = request.json
    if not data or "refreshToken" not in data:
        return jsonify({"error", "Invalid data"}), 400

    refresh_token = data.get("refreshToken")

    # Make a POST request to Google's OAuth2 token endpoint
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
        },
    )

    try:
        # Parse the response
        data = response.json()

        if "error" in data:
            return jsonify({"error": data["error"]}), 400

        # Return the refreshed token data
        return jsonify(
            {
                "access_token": data.get("access_token"),
                "id_token": data.get("id_token"),
                "expires_in": data.get("expires_in"),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400
