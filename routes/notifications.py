from flask import Blueprint, jsonify, request
from models import *
import json

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/notifications/subscribe/<int:id>', methods=['POST'])
def subscribe(id):
    data = request.json
    if not data:
        return jsonify({'error': 'Invalid data'}), 400

    sub = NotificationSubscription.query.filter_by(
        chaperone_id=id,
        subscription=json.dumps(data)
    ).first()

    if not sub:
        sub = NotificationSubscription(
            chaperone_id=id,                # type: ignore
            subscription=json.dumps(data)   # type: ignore
        )
        db.session.add(sub)
        db.session.commit()
        return jsonify({'message': 'Subscription created'}), 201

    return jsonify({'error': 'Subscription already exists'}), 409

@notifications_bp.route('/notifications/send/<int:id>', methods=['POST'])
def send_notification(id):
    data = request.json
    if not data:
        return jsonify({'error': 'Invalid data'}), 400
    
    from utils.notifications import send_notification
    send_notification(8, data['title'], data['message'], "/")
    return jsonify({'error': ''}), 200