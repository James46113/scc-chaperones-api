from datetime import datetime, timedelta
from csv import writer
from models import *
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
from googleapiclient.http import MediaFileUpload
from flask import current_app


def create_backup():
    print("Creating backup")
    try:
        with current_app.app_context():
            start = datetime(datetime.now().year, datetime.now().month - 1, 1)
            end = datetime(datetime.now().year, datetime.now().month,
                            1) - timedelta(days=1)

            with open(f"Backup-{start.strftime('%Y-%m')}.csv", "w") as f:
                csv = writer(f)
                csv.writerow(["Title", "Start (ALWAYS GMT)", "End (ALWAYS GMT)", "Details",
                                "Location", "Lead Chaperone", "Chaperones"])

                for event in Event.query.filter(Event.start >= start, Event.end <= end).all():
                    chaperone_slots = ChaperoneSlot.query.filter_by(
                        event_id=event.id).all()
                    chaperones = [Chaperone.query.get(
                        slot.chaperone).name for slot in chaperone_slots if slot.chaperone] #type: ignore

                    lead_chaperone = Chaperone.query.get(event.lead_chaperone)
                    if lead_chaperone:
                        lead_chaperone = lead_chaperone.name

                    csv.writerow([event.title, event.start,
                                    event.end, event.details, event.location, lead_chaperone, ", ".join(chaperones)])

            upload_file_to_drive(f"Backup-{start.strftime('%Y-%m')}.csv")
            print("Backup created")

    except Exception as e:
        print(f"Failed to create backup {str(e)}")


def upload_file_to_drive(file):
    scopes = 'https://www.googleapis.com/auth/drive'

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'chaperones-rota-93f9effba7f4.json', scopes)

    http_auth = credentials.authorize(Http())
    drive = build('drive', 'v3', http=http_auth)

    file_metadata = {'name': file, 'parents': [
        '1VEsRlIEBnpODAdoLrNh9evWsHv_g6sI5']}
    media = MediaFileUpload(file, mimetype='application/octet-stream')
    file = drive.files().create(body=file_metadata,
                                media_body=media, fields='id').execute()
    print(f'File ID: {file.get("id")}')

    print("Done")
