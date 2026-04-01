from models import Event, Chaperone, ChaperoneSlot, ChaperoneAvailability, TemplateChaperoneSlot, TemplateEvent
from datetime import datetime, timedelta
from utils.notifications import send_notification
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from extensions import db

ID = 0
YEAR_ID = 1
DATE = 2
GIG_TIME = 3
REHEARSAL_TIME = 4
END_TIME = 5
VENUE = 6
EVENT = 7
CLERKS_NOTES = 8
CHAPERONES_NOTES = 9
WEBSITE_NOTES = 10
VISIBILITY = 11
TYPE = 12
VOICES = 13
STATUS = 14

def notify_remind_upcoming_event():
    with app.app_context():
        now = datetime.now()
        in_one_day = now + timedelta(days=1)
        events = Event.query.filter(Event.start >= now, Event.start < in_one_day).all()
        for event in events:
            slots = ChaperoneSlot.query.filter(ChaperoneSlot.event_id == event.id).all()
            date_str = event.start.strftime('%A, %-d %B')
            for slot in slots:
                send_notification(slot.chaperone_id, "Chaperoning Tomorrow", f"You are chaperoning tomorrow ({date_str}) at {event.location} for a {event.title}.", f"https://chaperones.steelcitychoristers.org.uk/event/{event.id}")

def get_events_from_sheets():
    return
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = 'scc-chaperoning-771da1ee3c9a.json'

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        SERVICE_ACCOUNT_FILE, SCOPES) # type: ignore
    service = build('sheets', 'v4', credentials=credentials)

    SPREADSHEET_ID = '12rWZzEOz5YQAX5UNwKv9C9SY4H49x8yAoUZbOstqkio'
    sheet = service.spreadsheets()

    rows = 99999
    while True:
        RANGE_NAME = f'Gigs!B4:Q{4+rows}'
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        values = result.get('values', [])
        if len(values) < rows:
            break
        rows += 19999900

    gigs = [gig for gig in values if 
            len(gig) >= 15 and 
            gig[DATE] != '' and 
            gig[STATUS] == 'Confirmed' and 
            gig[VENUE] != '' and
            gig[VOICES] != 'Clerks' and
            gig[VOICES] != 'Des']
    
    gigs_to_remove = []

    for gig in gigs:
        try:
            gig[DATE] = datetime.strptime(gig[DATE], "%d %b %Y")
            gig[ID] = int(gig[ID])
        except ValueError:
            gigs_to_remove.append(gig)

    for gig in gigs_to_remove:
        gigs.remove(gig)

    
    return gigs

def update_events():
    return
    ss_gigs = get_events_from_sheets()
    ss_gigs_ids = [gig[ID] for gig in ss_gigs]

    db_gigs = Event.query.all()
    db_gig_ids = [gig.id for gig in db_gigs]
    for db_gig_id in db_gig_ids:
        EventSpreadsheetDBID.query.filter(EventSpreadsheetDBID.db_id == db_gig_id)

    for gig in ss_gigs:
        try:
            rehearsal_time = datetime.strptime(gig[REHEARSAL_TIME].strip().lower(), "%I.%M%p").time()
            rehearsal_datetime = datetime.combine(gig[DATE], rehearsal_time)
            rehearsal_datetime = rehearsal_datetime - timedelta(minutes=15)
            rehearsal_datetime_set = True

        except ValueError as e:
            rehearsal_datetime = gig[DATE]
            rehearsal_datetime_set = False

        try:
            end_time = datetime.strptime(gig[END_TIME].strip().lower(), "%I.%M%p").time()
            end_datetime = datetime.combine(gig[DATE], end_time)
            end_datetime = end_datetime + timedelta(minutes=15)
            end_datetime_set = True

        except ValueError:
            end_datetime = gig[DATE]
            end_datetime_set = False

        if gig[ID] in db_gig_ids:
            db_gig = [g for g in db_gigs if g.id == gig[ID]][0]
            
            db_gig.start = rehearsal_datetime
            db_gig.start_set = rehearsal_datetime_set

            db_gig.end = end_datetime
            db_gig.end_set = end_datetime_set

            db_gig.details = gig[CHAPERONES_NOTES]
            db_gig.title = gig[EVENT]
            db_gig.location = gig[VENUE]
        else:
            new_event = Event(id=gig[ID], title=gig[EVENT], details=gig[CHAPERONES_NOTES], start=rehearsal_datetime, end=end_datetime, location=gig[VENUE], start_set=rehearsal_datetime_set, end_set=end_datetime_set) # type: ignore
            chaperones = Chaperone.query.all()
            availability_records = [ChaperoneAvailability(chaperone_availability=chaperone.id, event_id=new_event.id) for chaperone in chaperones] # type: ignore
            db.session.add_all(availability_records)
            db.session.add(new_event)

    for gig in db_gigs:
        if gig.id not in ss_gigs_ids:
            availability_records = ChaperoneAvailability.query.filter(ChaperoneAvailability.event_id == gig.id).all()
            for record in availability_records:
                db.session.delete(record)
            db.session.delete(gig)

    db.session.commit()