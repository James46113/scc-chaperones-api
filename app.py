import logging
import time
from datetime import datetime
from os import getenv

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_cors import CORS

from extensions import db, migrate
from routes import register_blueprints
from utils.backup import create_backup
from utils.events import notify_remind_upcoming_event

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

load_dotenv(".env.local")

print(getenv("DEV"))
if getenv("DEV"):
    print("Running in development mode")
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+pymysql://root@localhost:3306/railway"
    )

else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "[DATABASE_URI]"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["CORS_HEADERS"] = "Content-Type"

db.init_app(app)
migrate.init_app(app, db)
register_blueprints(app)


@app.after_request
def after_request(response):
    response.headers.add(
        "Access-Control-Allow-Headers",
        "Content-Type,Authorization,fingerprint,token,last-updated",
    )
    return response


@app.errorhandler(503)
def service_unavailable(e):
    return jsonify({"error": f"Service Unavailable: {str(e)}"}), 503


@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok"}), 200


# Configure logging
if getenv("DEV"):
    logging.basicConfig(
        filename="app.log",  # Log file
        level=logging.INFO,  # Log level
        format="%(message)s",  # Log format
    )
else:
    logging.basicConfig(
        filename="/logs/app.log",  # Log file
        level=logging.INFO,  # Log level
        format="%(message)s",  # Log format
    )

werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.propagate = False

# Create a new logger for application-specific logs
app_logger = logging.getLogger("app_logger")
app_logger.setLevel(logging.INFO)


@app.before_request
def log_request_info():
    request.start_time = time.time()  # type: ignore


@app.after_request
def log_response_info(response):
    if request.method == "OPTIONS":
        return response

    elapsed_time = int((time.time() - request.start_time) * 1000)  # type: ignore
    try:
        name = g.user.name
    except AttributeError:
        name = ""

    werkzeug_logger.info(
        ",".join(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " GMT",
                name,
                request.method,
                request.path,
                response.status,
                str(elapsed_time) + "ms",
            ]
        )
    )
    return response


@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


scheduler = BackgroundScheduler()
logging.getLogger("apscheduler").propagate = False


# Suppress logging for the scheduler
scheduler.add_job(
    create_backup, "cron", day=1, hour=0, minute=0, misfire_grace_time=None
)
scheduler.add_job(notify_remind_upcoming_event, "cron", hour=9, minute=0)


scheduler.start()

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
