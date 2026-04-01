from flask import Blueprint, request, jsonify, g
from models import *
from utils.security import login_required, admin_required
from utils.misc import serialiseItem, serialiseItems
from utils.mail import send_mail, send_mail_many
from utils.notifications import broadcast_notification, send_notification
from smtplib import SMTP_SSL as SMTP
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import threading
from datetime import datetime
# import ics


chaperones_bp = Blueprint('chaperones', __name__)

@chaperones_bp.route('/chaperones/availability', methods=['GET'])
@login_required
@admin_required
def get_chaperones_availability():
    availability = ChaperoneAvailability.query.all()
    return jsonify(serialiseItems(availability))


@chaperones_bp.route('/chaperones/availability/<int:chaperone_id>', methods=['GET'])
@login_required
def get_chaperone_availability(chaperone_id):
    if g.user.id != chaperone_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    availability = ChaperoneAvailability.query.filter_by(
        chaperone_id=chaperone_id).all()
    return jsonify(serialiseItems(availability))


#UNUSED?
@chaperones_bp.route('/chaperones/availability/<int:chaperone_id>/<int:event_id>', methods=['GET'])
@login_required
@admin_required
def get_chaperone_event_availability(chaperone_id, event_id):
    availability = ChaperoneAvailability.query.get((event_id, chaperone_id))
    if availability:
        return jsonify(serialiseItem(availability))

    return jsonify({'error': 'Availability not found'}), 404


@chaperones_bp.route('/chaperones/availability/<int:chaperone_id>', methods=['PATCH'])
@login_required
def update_chaperones_availability(chaperone_id):
    if g.user.id != chaperone_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json

    if not data or 'event_id' not in data or 'available' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    chaperone_availability = ChaperoneAvailability.query.get(
        (data['event_id'], chaperone_id))
    if not chaperone_availability:
        return jsonify({'error': 'Availability not found'}), 404

    assigned = ChaperoneSlot.query.filter_by(
        event_id=data['event_id'], chaperone=chaperone_id).first()

    if assigned and data['available'] is False:
        destination = ['chaperones@steelcitychoristers.org.uk']

        chaperone = Chaperone.query.get(chaperone_id)
        if not chaperone:
            return jsonify({'error': 'Chaperone not found'}), 404

        event = Event.query.get(data['event_id'])
        if not event:
            return jsonify({'error': 'Event not found'}), 404


        html = f'{chaperone.name} has attempted to update their availability for the event: "{event.title}" on {event.start.strftime(("%A, %d %B"))} to unavailable, but they are already assigned to the event.\nThey have been told to contact you, but please ensure that the event is covered.\n\nSteel City Choristers Chaperone System'
        subject = f'Chaperone Unavailability - {event.start.strftime(("%A, %d %B"))}'

        email_thread = threading.Thread(target=send_mail, args=[destination, subject, html])
        email_thread.start()

        return jsonify({'error': 'Chaperone already assigned'}), 403

    chaperone_availability.available = data['available']
    db.session.commit()

    return jsonify({'error': ''}), 201



@chaperones_bp.route('/chaperones/events/email', methods=['POST'])
@login_required
@admin_required
def notify_chaperones_of_upcoming_assigned_events():
    try:
        messages = []

        with open('mail_templates/upcoming_events.html', 'r') as f:
            content = f.read()

        with open('mail_templates/footer.html', 'r') as f:
            footer = f.read()

        for chaperone in Chaperone.query.all():

            assigned_slots = ChaperoneSlot.query.filter_by(
                chaperone=chaperone.id).all()
            assigned_events = [Event.query.get(
                slot.event_id) for slot in assigned_slots if slot.start > datetime.now()]
            
            assigned_events.sort(key=lambda x: x.start) # type: ignore

            # ics_calendars = []

            # calendar = ics.Calendar()
            # for event in assigned_events:
            #     if not event:
            #         continue

            #     temp_calendar = ics.Calendar()
            #     temp_calendar.events.add(ics.Event(
            #         name="Chaperoning - Steel City Choristers",
            #         begin=event.start,
            #         end=event.end,
            #         location=event.location,
            #         description=event.title,
            #         url=f"https://steelcitychoristers.org.uk/events/{event.id}"
            #     ))
            #     ics_calendars.append(temp_calendar)

            destination = [chaperone.email]

            events_list = ['<li>' + event.start.strftime(
                '%A, %d %B - ') + event.title + '</li>' for event in assigned_events if event]

            if len(events_list) == 0:
                events_list = ['<li>No events assigned</li>']

            chaperone_content = content.replace('{{name}}', chaperone.name)
            chaperone_content = chaperone_content.replace(
                '{{events}}', ''.join(events_list))
            chaperone_content = chaperone_content.replace(
                '{{chaperone_id}}', str(chaperone.id))

            msg = MIMEMultipart('related')
            msg_text = MIMEText(chaperone_content + footer, 'html')
            msg.attach(msg_text)

            # for calendar in ics_calendars:
            #     calendar_attachment = MIMEText(
            #         calendar.serialize(), 'calendar')
            #     calendar_attachment.add_header(
            #         'Content-Disposition', 'attachment', filename='events.ics')
            #     msg.attach(calendar_attachment)

            # with open('mail_templates/Steel-City-Choristers.png', 'rb') as img_file:
            #     img = MIMEImage(img_file.read())
            #     img.add_header('Content-ID', '<logo>')
            #     msg.attach(img)

            # with open('mail_templates/alert-circle.png', 'rb') as img_file:
            #     img = MIMEImage(img_file.read())
            #     img.add_header('Content-ID', '<alert>')
            #     msg.attach(img)

            msg['Subject'] = f'Your Upcoming Events - Steel City Choristers'
            msg['From'] = 'chaperones@steelcitychoristers.org.uk'
            msg['To'] = ', '.join(destination)

            messages.append((destination, msg))

        
        send_mail_many(messages)
        broadcast_notification("Chaperone Rota Updated", "Open the app to view the updated chaperones' rota.")

        return jsonify({'error': ''}), 200
    except Exception as e:
        return jsonify({'error': f'Internal Server Error: {str(e)}'}), 500




@chaperones_bp.route('/chaperones', methods=['GET'])
@login_required
def get_users():
    last_read = request.headers.get('last-updated', type=int)
    all_users = Chaperone.query.all()
    try:
        users = Chaperone.query.filter(Chaperone.last_updated > last_read).all()
    except Exception as e:
        users = all_users

    if g.user.is_admin:
        users = [{'id': user.id, 'email': user.email,
              'is_admin': user.is_admin, 'name': user.name, 'is_singing_chaperone': user.is_singing_chaperone, 'last_login': user.last_login} for user in users]
    else:
        users = [{'id': user.id,
              'name': user.name, 'is_singing_chaperone': user.is_singing_chaperone} for user in users]
    
    return jsonify({"chaperones": users,
            "chaperone_ids": [user.id for user in all_users]})


@chaperones_bp.route('/chaperones', methods=['PUT'])
@login_required
@admin_required
def create_user():
    data = request.json

    if not data or 'email' not in data or 'is_admin' not in data or 'name' not in data or 'is_singing_chaperone' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    if Chaperone.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'User already exists'}), 409

    user = Chaperone(
        email=data['email'], is_admin=data['is_admin'], name=data['name'], is_singing_chaperone=data['is_singing_chaperone']) # type: ignore
    db.session.add(user)

    for event in Event.query.all():
        chaperone_availability = ChaperoneAvailability(
            event_id=event.id, chaperone_id=user.id, available=None) # type: ignore
        db.session.add(chaperone_availability)

    db.session.commit()
    return jsonify({'email': user.email, 'is_admin': user.is_admin, 'id': user.id, 'name': user.name}), 201


@chaperones_bp.route('/chaperones/events', methods=['GET'])
@login_required
def get_chaperones_events():
    chaperones = Chaperone.query.all()
    chaperones_events = []
    for chaperone in chaperones:
        chaperone_slots = ChaperoneSlot.query.filter_by(
            chaperone=chaperone.id).all()
        events = [Event.query.get(chaperone_slot.event_id)
                  for chaperone_slot in chaperone_slots]

        events = [event for event in events if event and event.start > datetime.now()]

        events = list({event.id: event for event in events}.values())

        chaperones_events.append(
            {'chaperone_id': chaperone.id, 'events': len(events)})

    return jsonify(chaperones_events)


@chaperones_bp.route('/chaperones/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(id):  # update
    user = Chaperone.query.get(id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.name == "Choir Phone":
        return jsonify({'error': 'Cannot delete admin'}), 403

    for availability in ChaperoneAvailability.query.filter_by(chaperone_id=id).all():
        db.session.delete(availability)

    for token in AccessToken.query.filter_by(chaperone_id=id).all():
        db.session.delete(token)

    for slot in ChaperoneSlot.query.filter_by(chaperone=id).all():
        slot.chaperone = None

    db.session.delete(user)
    db.session.commit()
    return jsonify({'error': ''}), 200


@chaperones_bp.route('/chaperones/<int:id>', methods=['GET'])
@login_required
@admin_required
def get_user(id):
    user = Chaperone.query.get(id)
    if not user:
        return jsonify({'error': 'Chaperone not found'}), 404
    
    return jsonify({'id': user.id, 'email': user.email, 'is_admin': user.is_admin, 'name': user.name})


@chaperones_bp.route('/chaperones/<int:id>', methods=['PATCH'])
@login_required
@admin_required
def update_user(id):
    data = request.json
    user = Chaperone.query.get(id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if not data:
        return jsonify({'error': 'Invalid data'}), 400

    if 'is_admin' in data:
        if user.name == "Choir Phone":
            return jsonify({'error': 'Cannot change admin status'}), 403
        else:
            user.is_admin = data['is_admin']

    if 'email' in data:
        user.email = data['email']

    if 'is_singing_chaperone' in data:
        user.is_singing_chaperone = data['is_singing_chaperone']

    db.session.commit()
    return jsonify({'id': user.id, 'email': user.email, 'is_admin': user.is_admin, 'name': user.name}), 200


@chaperones_bp.route('/availability/mail', methods=['POST'])
@login_required
@admin_required
def send_availability_mail():
    try:
        sender = "chaperones@steelcitychoristers.org.uk"

        chaperones = Chaperone.query.all()

        # HTML content with an embedded image

        with open('mail_templates/availability.html', 'r') as f:
            main_content = f.read()

        with open('mail_templates/footer.html', 'r') as f:
            footer = f.read()

        html_content = main_content + footer

        messages = []

        for chaperone in chaperones:

            print(f"Sending availability reminder to {chaperone.email}")

            notGivenAvailabilities = []
            for availability in ChaperoneAvailability.query.filter_by(
                chaperone_id=chaperone.id, available=None).all():
                event = Event.query.get(availability.event_id)
                if event and event.start > datetime.now():
                    notGivenAvailabilities.append((event.start, event.title))

            notGivenAvailabilities.sort(key=lambda x: x[0])

            if len(notGivenAvailabilities) == 0:
                continue

            send_notification(chaperone.id, "Availability", "Please give your availability for upcoming events.", "/")

            notGivenAvailabilitiesUL = "".join(
                [f"<li>{start.strftime('%A, %d %B - ')}{title}</li>" for start, title in notGivenAvailabilities]
            )

            temp_content = html_content

            temp_content = temp_content.replace("{{name}}", chaperone.name)
            temp_content = temp_content.replace(
                "{{events}}", notGivenAvailabilitiesUL)

            subject = "Chaperoning Availability - Steel City Choristers"
            destination = [chaperone.email]

            # Create the root message

            # Create the body with HTML content
            html = temp_content

            # with open('mail_templates/Steel-City-Choristers.png', 'rb') as img_file:
            #     img = MIMEImage(img_file.read())
            #     img.add_header('Content-ID', '<logo>')
            #     msg.attach(img)

            messages.append((destination, subject, html))

        
        t = threading.Thread(target=send_mail_many, args=(messages,))
        t.start()
    except Exception as e:
        return jsonify({"error": "failed to send mail; %s" % str(e)}), 500

    return jsonify({'error': ''}), 200