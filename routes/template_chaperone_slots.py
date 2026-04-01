from flask import Blueprint, request, jsonify
from models import *
from utils.security import login_required, admin_required
from utils.misc import serialiseItem, serialiseItems
from datetime import datetime

template_slots_bp = Blueprint('template_slots', __name__)


@template_slots_bp.route('/template_chaperone_slots', methods=['GET'])
@login_required
def get_template_chaperone_slots():
    last_read = request.headers.get('last-updated', type=int)
    all_template_chaperone_slots = TemplateChaperoneSlot.query.all()
    try:
        template_chaperone_slots = TemplateChaperoneSlot.query.filter(
            TemplateChaperoneSlot.last_updated > last_read).all()
    except Exception as e:
        #print(e)
        template_chaperone_slots = all_template_chaperone_slots
    

    return jsonify({
        "template_slots": serialiseItems(template_chaperone_slots),
        "template_slot_ids": [slot.id for slot in all_template_chaperone_slots]
        })


@template_slots_bp.route('/template_chaperone_slots/<int:template_id>', methods=['GET'])
@login_required
def get_template_chaperone_slot(template_id):
    template_chaperone_slot = TemplateChaperoneSlot.query.filter_by(
        template_id=template_id).all()
    return jsonify(serialiseItems(template_chaperone_slot))


@template_slots_bp.route('/template_chaperone_slots', methods=['PUT'])
@login_required
@admin_required
def create_template_chaperone_slot():
    data = request.json

    if not data or 'start' not in data or 'end' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    start = datetime.strptime(
        data['start'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    end = datetime.strptime(
        data['end'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')

    template_chaperone_slot = TemplateChaperoneSlot(
        template_id=data['template_id'], start=start, end=end, title=data['title']) # type: ignore

    if 'details' in data:
        template_chaperone_slot.details = data['details']

    db.session.add(template_chaperone_slot)
    db.session.commit()
    return jsonify({'id': template_chaperone_slot.id}), 201



@template_slots_bp.route('/template_chaperone_slots/<int:slot_id>', methods=['PATCH'])
@login_required
@admin_required
def update_template_chaperone_slot(slot_id):
    data = request.json
    if not data:
        return jsonify({'error', 'Invalid data'}), 400
    
    template_chaperone_slot = TemplateChaperoneSlot.query.get(slot_id)

    if not template_chaperone_slot:
        return jsonify({'error', 'Template chaperone slot not found'}), 404

    if 'title' in data:
        template_chaperone_slot.title = data['title']
    if 'details' in data:
        template_chaperone_slot.details = data['details']
    if 'start' in data:
        template_chaperone_slot.start = datetime.strptime(
            data['start'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    if 'end' in data:
        template_chaperone_slot.end = datetime.strptime(
            data['end'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    db.session.commit()
    return jsonify({'error': ''}), 200


@template_slots_bp.route('/template_chaperone_slots/<int:template_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_template_chaperone_slot(template_id):
    template_chaperone_slots = TemplateChaperoneSlot.query.filter_by(
        id=template_id).all()
    for slot in template_chaperone_slots:
        db.session.delete(slot)
    db.session.commit()
    return jsonify({'error': ''}), 204