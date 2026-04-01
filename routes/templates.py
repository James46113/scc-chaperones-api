from flask import Blueprint, request, jsonify
from models import *
from utils.security import login_required, admin_required
from utils.misc import serialiseItem, serialiseItems
from datetime import datetime

templates_bp = Blueprint('templates', __name__)



@templates_bp.route('/templates', methods=['GET'])
@login_required
def get_templates():
    last_read = request.headers.get('last-updated', type=int)
    all_templates = TemplateEvent.query.all()
    try:
        templates = TemplateEvent.query.filter(
            TemplateEvent.last_updated > last_read).all()
    except Exception as e:
        #print(e)
        templates = all_templates

    return jsonify({
        "templates": serialiseItems(templates),
        "template_ids": [template.id for template in all_templates]
        })


@templates_bp.route('/templates/list', methods=['GET'])
@login_required
def get_templates_list():
    templates = TemplateEvent.query.all()
    templates_list = [
        {'id': template.id, 'template_name': template.template_name} for template in templates]
    return jsonify(templates_list)


@templates_bp.route('/templates', methods=['PUT'])
@login_required
@admin_required
def create_template():
    data = request.json

    if not data or 'start' not in data or 'end' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    start = datetime.strptime(
        data['start'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    end = datetime.strptime(
        data['end'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')

    template = TemplateEvent(title=data['title'], start=start, end=end, location=data['location'], template_name=data['template_name']) # type: ignore

    if 'details' in data:
        template.details = data['details']

    if 'juniors_present' in data:
        template.juniors_present = data['juniors_present']

    db.session.add(template)
    db.session.commit()
    return jsonify({'id': template.id}), 201



@templates_bp.route('/templates/<int:template_id>', methods=['GET'])
@login_required
def get_template(template_id):
    template = TemplateEvent.query.get(template_id)
    return jsonify(serialiseItem(template))

@templates_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_template(template_id):
    template = TemplateEvent.query.get(template_id)

    if int(template_id) in [2, 3]:
        return jsonify({'error': 'Cannot delete default templates'}), 403

    slots = TemplateChaperoneSlot.query.filter_by(
        template_id=template_id).all()

    for slot in slots:
        db.session.delete(slot)

    db.session.delete(template)
    db.session.commit()
    return jsonify({'error': ''}), 200


@templates_bp.route('/templates/<int:template_id>', methods=['PATCH'])
@login_required
@admin_required
def update_template(template_id):
    data = request.json
    template = TemplateEvent.query.get(template_id)

    if not data:
        return jsonify({'error': 'Invalid data'}), 400
    
    if not template:
        return jsonify({'error': 'Template not found'}), 404

    if 'title' in data:
        template.title = data['title']
    if 'details' in data:
        template.details = data['details']
    if 'start' in data:
        template.start = datetime.strptime(
            data['start'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    if 'end' in data:
        template.end = datetime.strptime(
            data['end'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    if 'location' in data:
        template.location = data['location']
    if 'template_name' in data:
        template.template_name = data['template_name']
    if 'juniors_present' in data:
        template.juniors_present = data['juniors_present']
    db.session.commit()
    return jsonify({'error': ''}), 200
