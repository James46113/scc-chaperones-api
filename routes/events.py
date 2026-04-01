from flask import Blueprint, request, jsonify
from models import *
from utils.security import login_required, admin_required
from utils.misc import serialiseItem, serialiseItems
from datetime import datetime, timedelta
from pytz import timezone
import pytz

events_bp = Blueprint('events', __name__)


@events_bp.route('/events', methods=['GET'])
@login_required
def get_events():
    last_read = request.headers.get('last-updated', type=int)
    all_events = Event.query.all()
    try:
        events = Event.query.filter(Event.last_updated > last_read).all()
    except Exception as e:
        #print(e)
        events = all_events

    return jsonify({
        "events": serialiseItems(events),
        "event_ids": [event.id for event in all_events]
        })


@events_bp.route('/events', methods=['PUT'])
@login_required
@admin_required
def create_event():
    data = request.json

    if not data or 'start' not in data or 'end' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    start = datetime.strptime(
        data['start'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    end = datetime.strptime(
        data['end'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')

    event = Event(title=data['title'], start=start, end=end, location=data['location']) # type: ignore

    if 'lead_chaperone' in data:
        event.lead_chaperone = data['lead_chaperone']

    if 'details' in data:
        event.details = data['details']

    if 'juniors_present' in data:
        event.juniors_present = data['juniors_present']

    db.session.add(event)

    for chaperone in Chaperone.query.all():
        chaperone_availability = ChaperoneAvailability(
            event_id=event.id, chaperone_id=chaperone.id, available=None) # type: ignore
        db.session.add(chaperone_availability)

    db.session.commit()
    return jsonify({'id': event.id}), 201



@events_bp.route('/events/<int:event_id>', methods=['GET'])
@login_required
def get_event(event_id):
    event = Event.query.get(event_id)
    return jsonify(serialiseItem(event))


@events_bp.route('/events/<int:event_id>/availability', methods=['GET'])
@login_required
def get_event_availability(event_id):
    availability = ChaperoneAvailability.query.filter_by(
        event_id=event_id).all()
    return jsonify(serialiseItems(availability))


@events_bp.route('/events/<int:event_id>/<int:chaperone>', methods=['GET'])
@login_required
def get_event_for_chaperone(event_id, chaperone):
    chaperone_slots = ChaperoneSlot.query.filter_by(
        event_id=event_id, chaperone=chaperone).all()
    return jsonify(serialiseItems(chaperone_slots))


@events_bp.route('/events/chaperone/<int:chaperone_id>', methods=['GET'])
@login_required
def get_events_for_chaperone(chaperone_id):
    chaperone_slots = ChaperoneSlot.query.filter(
        ChaperoneSlot.chaperone == chaperone_id and ChaperoneSlot.end > datetime.now()).all()
    events = [Event.query.get(chaperone_slot.event_id)
              for chaperone_slot in chaperone_slots]
    unique_events = {event.id: event for event in events if event}.values()
    return jsonify(serialiseItems(unique_events))


@events_bp.route('/events/<int:event_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_event(event_id):
    event = Event.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404

    if event.end < datetime.now():
        return jsonify({'error': 'Cannot delete past event'}), 400

    db.session.delete(event)

    for availability in ChaperoneAvailability.query.filter_by(event_id=event_id).all():
        db.session.delete(availability)

    for slot in ChaperoneSlot.query.filter_by(event_id=event_id).all():
        db.session.delete(slot)

    db.session.commit()
    return jsonify({'error': ''}), 200


@events_bp.route('/events/<int:event_id>', methods=['PATCH'])
@login_required
@admin_required
def update_event(event_id):
    data = request.json
    event = Event.query.get(event_id)

    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    if not data:
        return jsonify({'error': 'Invalid data'}), 400

    if event.start < datetime.now() - timedelta(days=2):
        return jsonify({'error': 'Cannot update past event'}), 400

    if 'title' in data:
        event.title = data['title']
    if 'details' in data:
        event.details = data['details']
    if 'start' in data:
        event.start = datetime.strptime(
            data['start'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    if 'end' in data:
        event.end = datetime.strptime(
            data['end'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    if 'location' in data:
        event.location = data['location']
    if 'lead_chaperone' in data:
        event.lead_chaperone = data['lead_chaperone']

    if 'juniors_present' in data:
        event.juniors_present = data['juniors_present']
        
    db.session.commit()
    return jsonify({'error': ''}), 200


@events_bp.route('/events_chaperones', methods=['GET'])
@login_required
def get_chaperones_for_events():
    chaperones = [
        (chaperone_slot.chaperone, chaperone_slot.event_id) for chaperone_slot in ChaperoneSlot.query.all()]

    chaperones_dict = {}
    for chaperone, event_id in chaperones:
        if event_id not in chaperones_dict:
            chaperones_dict[event_id] = []
        chaperones_dict[event_id].append(chaperone)

    result = [{'event_id': event_id, 'chaperones': chaperones}
              for event_id, chaperones in chaperones_dict.items()]

    return jsonify(result)


@events_bp.route('/create_term', methods=['PUT'])
@login_required
@admin_required
def create_term():
    data = request.json
    if 'start' not in data:
        return jsonify({'error': 'Start date required'}), 400
    
    if 'end' not in data:
        return jsonify({'error': 'End date required'}), 400

    # create datetime from timestamp (milliseconds only)
    ts = int(data['start'])
    start = datetime.fromtimestamp(ts / 1000)

    ts = int(data['end'])
    end = datetime.fromtimestamp(ts / 1000)

    while start <= end:
        if start.weekday() == 0:  # Monday 
            if not create_event_from_template(2, start): # template id
                return jsonify({'error': 'An error occurred'}), 500
        elif start.weekday() == 4: # Friday
            if not create_event_from_template(3, start): # template id
                return jsonify({'error': 'An error occurred'}), 500        
        start += timedelta(days=1)
    
    return jsonify({}), 201


def create_event_from_template(template_id: int, date: datetime):

    uk_tz = timezone('Europe/London')
    template = TemplateEvent.query.get(template_id)
    template_slots = TemplateChaperoneSlot.query.filter_by(template_id=template_id).all()
    if not template or not template_slots:
        return False

    # Adjust for daylight saving time
    start_time = datetime.combine(date, template.start.time())
    end_time = datetime.combine(date, template.end.time())
    if uk_tz.localize(start_time).dst() != timedelta(0):
        start_time -= timedelta(hours=1)
        end_time -= timedelta(hours=1)

    event = Event(
        title=template.title,
        details=template.details,
        start=start_time,
        end=end_time,
        location=template.location,
        juniors_present=template.juniors_present
    )
    db.session.add(event)
    db.session.flush()

    for chaperone in Chaperone.query.all():
        chaperone_availability = ChaperoneAvailability(
            event_id=event.id, chaperone_id=chaperone.id, available=None) # type: ignore
        db.session.add(chaperone_availability)

    for slot in template_slots:
        slot_start = datetime.combine(date, slot.start.time())
        slot_end = datetime.combine(date, slot.end.time())
        # Adjust for daylight saving time
        if uk_tz.localize(slot_start).dst() != timedelta(0):
            slot_start -= timedelta(hours=1)
            slot_end -= timedelta(hours=1)

        new_slot = ChaperoneSlot(
            event_id=event.id,
            start=slot_start,
            end=slot_end,
            details=slot.details,
            title=slot.title
        )
        db.session.add(new_slot)

    db.session.commit()
    return True
