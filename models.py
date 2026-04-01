from extensions import db
from sqlalchemy.sql import func

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    details = db.Column(db.String(9999), nullable=True)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    lead_chaperone = db.Column(db.Integer, nullable=True)
    last_updated = db.Column(db.Integer, onupdate=func.unix_timestamp(func.now()), default=func.unix_timestamp(func.now()), nullable=False)
    juniors_present = db.Column(db.Boolean, nullable=False, default=False)
    # start_set = db.Column(db.Boolean, nullable=False, default=True)
    # end_set = db.Column(db.Boolean, nullable=False, default=True)

class ChaperoneSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    chaperone = db.Column(db.Integer, nullable=True)
    details = db.Column(db.String(9999), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    last_updated = db.Column(db.Integer, onupdate=func.unix_timestamp(func.now()), default=func.unix_timestamp(func.now()), nullable=False)


class TemplateEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    details = db.Column(db.String(9999), nullable=True)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    template_name = db.Column(db.String(255), nullable=False)
    last_updated = db.Column(db.Integer, onupdate=func.unix_timestamp(func.now()), default=func.unix_timestamp(func.now()), nullable=False)
    juniors_present = db.Column(db.Boolean, nullable=False, default=False)


class TemplateChaperoneSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    template_id = db.Column(db.Integer, nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    details = db.Column(db.String(9999), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    last_updated = db.Column(db.Integer, onupdate=func.unix_timestamp(func.now()), default=func.unix_timestamp(func.now()), nullable=False)


class Chaperone(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    password_reset_token = db.Column(db.String(255), nullable=True)
    password_reset_expiry = db.Column(db.DateTime, nullable=True)
    last_updated = db.Column(db.Integer, onupdate=func.unix_timestamp(func.now()), default=func.unix_timestamp(func.now()), nullable=False)
    is_singing_chaperone = db.Column(db.Boolean, nullable=False, default=False)
    last_login = db.Column(db.DateTime, nullable=True)

class ChaperoneAvailability(db.Model):
    event_id = db.Column(db.Integer, primary_key=True)
    chaperone_id = db.Column(db.Integer, primary_key=True)
    available = db.Column(db.Boolean, nullable=True)
    last_updated = db.Column(db.Integer, onupdate=func.unix_timestamp(func.now()), default=func.unix_timestamp(func.now()), nullable=False)


class AccessToken(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(255), nullable=False)
    fingerprint = db.Column(db.String(255), nullable=False)
    chaperone_id = db.Column(db.Integer, nullable=False)


class NotificationSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chaperone_id = db.Column(db.Integer, nullable=False)
    subscription = db.Column(db.String(9999), nullable=False)


# class EventSpreadsheetDBID(db.Model):
#     db_id = db.Column(db.Integer, nullable=False)
#     ss_id = db.Column(db.Integer, nullable=False)