from flask import Blueprint, request, jsonify
from models import *
from utils.security import login_required, admin_required
from utils.misc import serialiseItem, serialiseItems
from datetime import datetime

chaperone_slots_bp = Blueprint('chaperone_slots', __name__)


@chaperone_slots_bp.route('/chaperone_slots', methods=['GET'])
@login_required
def get_all_chaperone_slots():
    last_read = request.headers.get('last-updated', type=int)
    all_slots = ChaperoneSlot.query.all()
    try:
        chaperone_slots = ChaperoneSlot.query.filter(
            ChaperoneSlot.last_updated > last_read).all()
    except Exception as e:
        #print(e)
        chaperone_slots = all_slots
    return jsonify({ 
        "slots": serialiseItems(chaperone_slots),
        "slot_ids": [slot.id for slot in all_slots]
        })


@chaperone_slots_bp.route('/chaperone_slots/<int:slot_id>', methods=['PATCH'])
@login_required
@admin_required
def update_chaperone_slot(slot_id):
    data = request.json
    chaperone_slot = ChaperoneSlot.query.get(slot_id)
    if data is None:
        return jsonify({'error': 'Invalid Data'}), 400
    
    if chaperone_slot is None:
        return jsonify({'error': 'Chaperone Slot not found'}), 404

    if 'title' in data:
        chaperone_slot.title = data['title']
    if 'details' in data:
        chaperone_slot.details = data['details']
    if 'start' in data:
        chaperone_slot.start = datetime.strptime(
            data['start'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    if 'end' in data:
        chaperone_slot.end = datetime.strptime(
            data['end'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    if 'chaperone' in data:
        chaperone_slot.chaperone = data['chaperone']
    db.session.commit()
    return jsonify({'error': ''}), 200


@chaperone_slots_bp.route('/chaperone_slots/<int:event_id>', methods=['GET'])
@login_required
def get_chaperone_slot(event_id):
    chaperone_slot = ChaperoneSlot.query.filter_by(event_id=event_id).all()
    return jsonify(serialiseItems(chaperone_slot))


@login_required
@chaperone_slots_bp.route('/chaperone_slots/chaperone/<int:chaperone_id>', methods=['GET'])
def get_chaperone_slots(chaperone_id):
    chaperone_slots = ChaperoneSlot.query.filter_by(
        chaperone=chaperone_id).all()
    return jsonify(serialiseItems(chaperone_slots))


@chaperone_slots_bp.route('/chaperone_slots', methods=['PUT'])
@login_required
@admin_required
def create_chaperone_slot():
    data = request.json

    if not data or 'start' not in data or 'end' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    start = datetime.strptime(
        data['start'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    end = datetime.strptime(
        data['end'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')

    chaperone_slot = ChaperoneSlot(
        event_id=data['event_id'], start=start, end=end, title=data['title']) # type: ignore

    if 'chaperone' in data:
        chaperone_slot.chaperone = data['chaperone']

    if 'details' in data:
        chaperone_slot.details = data['details']

    db.session.add(chaperone_slot)
    db.session.commit()
    return jsonify({'id': chaperone_slot.id}), 201



@chaperone_slots_bp.route('/chaperone_slots/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_chaperone_slot(id):
    slot = ChaperoneSlot.query.get(id)
    db.session.delete(slot)
    db.session.commit()
    return jsonify({'error': ''}), 200


@chaperone_slots_bp.route('/chaperone_slots/event/<int:event_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_chaperone_slots_by_event(event_id):
    chaperone_slots = ChaperoneSlot.query.filter_by(event_id=event_id).all()
    for slot in chaperone_slots:
        db.session.delete(slot)
    db.session.commit()
    return jsonify({'error': ''}), 200

