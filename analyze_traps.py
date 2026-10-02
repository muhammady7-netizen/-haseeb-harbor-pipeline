import json
path = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\harbor-jobs-t1\oracle-answer-v5\the-answer-she-already-gave__5QfXVgE\agent\trajectory.json'
t = json.load(open(path, 'r', encoding='utf-8'))
obs = t['steps'][0]['observation']
results = obs.get('results', [])
content = results[0].get('content', '')
outer = json.loads(content)
inner = json.loads(outer['result'])
events = inner['results'][0]['events']

# Build a complete picture
print('=== ALL 9 EVENTS ===')
all_attendees = set()
real_meetings = []
non_real = []
for e in events:
    title = e.get('summary', '?')
    etype = e.get('eventType', '?')
    status = e.get('status', '?')
    org = e.get('organizer_email', '?')
    attendees = e.get('attendees', [])
    is_real = (etype == 'default' and status == 'confirmed' and org == 'nathan.thomas@maplewoodhospital.org')
    tag = 'REAL' if is_real else 'NON-REAL'
    print('%s | %s | type=%s status=%s org=%s attendees=%d' % (tag, title, etype, status, org, len(attendees)))
    for a in attendees:
        email = a.get('email', '?')
        opt = a.get('optional', '?')
        resp = a.get('responseStatus', '?')
        all_attendees.add(email)
        print('  %s opt=%s resp=%s' % (email, opt, resp))
    if is_real:
        real_meetings.append(e)
    else:
        non_real.append(e)

print()
print('=== CROSS-REFERENCES ===')
print('Real meetings:', len(real_meetings))
print('Non-real events:', len(non_real))
print('Unique attendee emails:', len(all_attendees))

# Morgan Thompson appearances
morgan_events = []
for e in events:
    for a in e.get('attendees', []):
        if 'morgan.thompson' in a.get('email', ''):
            title = e.get('summary', '?')
            status = e.get('status', '?')
            etype = e.get('eventType', '?')
            org = e.get('organizer_email', '?')
            is_real = (etype == 'default' and status == 'confirmed' and org == 'nathan.thomas@maplewoodhospital.org')
            morgan_events.append((title, status, a.get('responseStatus'), 'real' if is_real else 'non-real'))
print('Morgan Thompson events:', morgan_events)

# Nicole Washington appearances
nicole_events = []
for e in events:
    for a in e.get('attendees', []):
        if 'nicole.washington' in a.get('email', ''):
            title = e.get('summary', '?')
            is_real = (e.get('eventType') == 'default' and e.get('status') == 'confirmed' and e.get('organizer_email') == 'nathan.thomas@maplewoodhospital.org')
            nicole_events.append((title, a.get('optional'), a.get('responseStatus'), 'real' if is_real else 'non-real'))
print('Nicole Washington events:', nicole_events)

# Same title different events
titles = {}
for e in events:
    t = e.get('summary', '?')
    if t not in titles:
        titles[t] = []
    titles[t].append(e.get('event_id', '?'))
print('Duplicate titles:', {k: len(v) for k, v in titles.items() if len(v) > 1})

# Attendees on both real and non-real
real_emails = set()
non_real_emails = set()
for e in real_meetings:
    for a in e.get('attendees', []):
        real_emails.add(a.get('email', '?'))
for e in non_real:
    for a in e.get('attendees', []):
        non_real_emails.add(a.get('email', '?'))
both = real_emails & non_real_emails
print('On both real and non-real:', len(both), both)

# Total attendee entries across all events
total_entries = sum(len(e.get('attendees', [])) for e in events)
print('Total attendee entries all events:', total_entries)

# Optional accepted on real meetings
opt_accepted = 0
for e in real_meetings:
    for a in e.get('attendees', []):
        if a.get('optional') == True and a.get('responseStatus') == 'accepted':
            opt_accepted += 1
print('Optional accepted on real meetings:', opt_accepted)

# Required tentative on real meetings
req_tentative = 0
for e in real_meetings:
    for a in e.get('attendees', []):
        if a.get('optional') == False and a.get('responseStatus') == 'tentative':
            req_tentative += 1
print('Required tentative on real meetings:', req_tentative)
