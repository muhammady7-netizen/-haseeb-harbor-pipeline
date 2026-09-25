# -*- coding: utf-8 -*-
"""Generate 3 new multi-step reasoning chains for gen-g806 (v19).

Adds 200 scripts (SC-2296..SC-2495) across three chains:
  Chain 1: Scripture citation format validation (80 scripts, SC-2296..SC-2375)
  Chain 2: Timing adjustment cap (60 scripts, SC-2376..SC-2435)
  Chain 3: Presenter endorsement exception (60 scripts, SC-2436..SC-2495)

Each new rule is a SUB-CHECK of an existing rule (no new finding codes):
  - scripture format  -> sub-check of UNCITED_SCRIPTURE_REF
  - timing cap        -> sub-check of RUNTIME_OUT_OF_BAND (changes effective minutes)
  - endorsement       -> sub-check of NEGATION_PIVOT_USED (changes testimony exemption)

The timing cap is a GLOBAL rule, so it is applied to ALL scripts (existing + new).
This changes 12 existing fair-hurdle scripts whose |adjustment| > 50% of timed.
The golden is recomputed for every script with ALL rules (old + new) so it stays
100% consistent with the stated errata.
"""
import csv, json, re
from pathlib import Path
from collections import Counter

TASK = Path(r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\gen-g806-leadership-brief-rhetorical-style-audit')
INPUT = TASK / 'environment' / 'input'
SOL = TASK / 'solution' / 'files'
VERIFIER = TASK / 'tests' / 'verifier.json'

# Band bounds (latest effective_date 2026-09-01 active rows)
SMIN, SMAX, EMIN, EMAX = 4, 7, 6, 10
BANDS = {'standard': (SMIN, SMAX), 'extended': (EMIN, EMAX)}

# ----------------------------------------------------------------------
# Scripture registry
# ----------------------------------------------------------------------
# (book, chapter, verse_range, canonical_form)
REGISTRY = [
    ('Genesis', 1, '1-31', 'Genesis 1:1-31'),
    ('Genesis', 3, '1-24', 'Genesis 3:1-24'),
    ('Genesis', 12, '1-9', 'Genesis 12:1-9'),
    ('Genesis', 50, '1-26', 'Genesis 50:1-26'),
    ('Exodus', 3, '1-22', 'Exodus 3:1-22'),
    ('Exodus', 14, '1-31', 'Exodus 14:1-31'),
    ('Exodus', 20, '1-26', 'Exodus 20:1-26'),
    ('Psalms', 1, '1-6', 'Psalms 1:1-6'),
    ('Psalms', 23, '1-6', 'Psalms 23:1-6'),
    ('Psalms', 51, '1-19', 'Psalms 51:1-19'),
    ('Psalms', 91, '1-16', 'Psalms 91:1-16'),
    ('Psalms', 100, '1-5', 'Psalms 100:1-5'),
    ('Psalms', 119, '1-176', 'Psalms 119:1-176'),
    ('Proverbs', 1, '1-33', 'Proverbs 1:1-33'),
    ('Proverbs', 3, '1-35', 'Proverbs 3:1-35'),
    ('Proverbs', 16, '1-33', 'Proverbs 16:1-33'),
    ('Proverbs', 27, '1-27', 'Proverbs 27:1-27'),
    ('Isaiah', 6, '1-13', 'Isaiah 6:1-13'),
    ('Isaiah', 40, '1-31', 'Isaiah 40:1-31'),
    ('Isaiah', 53, '1-12', 'Isaiah 53:1-12'),
    ('Matthew', 5, '1-48', 'Matthew 5:1-48'),
    ('Matthew', 6, '1-34', 'Matthew 6:1-34'),
    ('Matthew', 28, '1-20', 'Matthew 28:1-20'),
    ('Mark', 1, '1-45', 'Mark 1:1-45'),
    ('Mark', 16, '1-20', 'Mark 16:1-20'),
    ('Luke', 1, '1-80', 'Luke 1:1-80'),
    ('Luke', 15, '1-32', 'Luke 15:1-32'),
    ('Luke', 24, '1-53', 'Luke 24:1-53'),
    ('John', 1, '1-51', 'John 1:1-51'),
    ('John', 3, '1-36', 'John 3:1-36'),
    ('John', 14, '1-31', 'John 14:1-31'),
    ('Acts', 1, '1-26', 'Acts 1:1-26'),
    ('Acts', 2, '1-47', 'Acts 2:1-47'),
    ('Acts', 9, '1-43', 'Acts 9:1-43'),
    ('Romans', 1, '1-32', 'Romans 1:1-32'),
    ('Romans', 8, '1-39', 'Romans 8:1-39'),
    ('Romans', 12, '1-21', 'Romans 12:1-21'),
    ('1 Corinthians', 13, '1-13', '1 Corinthians 13:1-13'),
    ('2 Corinthians', 5, '1-21', '2 Corinthians 5:1-21'),
    ('Galatians', 5, '1-26', 'Galatians 5:1-26'),
    ('Ephesians', 2, '1-22', 'Ephesians 2:1-22'),
    ('Philippians', 4, '1-23', 'Philippians 4:1-23'),
    ('Hebrews', 11, '1-40', 'Hebrews 11:1-40'),
    ('James', 1, '1-27', 'James 1:1-27'),
    ('1 John', 4, '1-21', '1 John 4:1-21'),
    ('Revelation', 21, '1-27', 'Revelation 21:1-27'),
    ('Revelation', 22, '1-21', 'Revelation 22:1-21'),
]

# A pool of valid full citations (book chapter:verse within range) for assigning
# existing has_ref=true&cited=true scripts a valid scripture_text.
VALID_CITATIONS = [
    'Genesis 1:1', 'Genesis 3:15', 'Exodus 20:3', 'Psalms 23:1', 'Psalms 91:1',
    'Psalms 51:10', 'Proverbs 3:5', 'Isaiah 53:5', 'Matthew 5:3', 'Matthew 6:9',
    'Mark 16:6', 'Luke 15:4', 'John 3:16', 'John 14:6', 'Acts 2:1',
    'Romans 8:28', 'Romans 12:1', '1 Corinthians 13:1', '2 Corinthians 5:17',
    'Galatians 5:22', 'Ephesians 2:8', 'Philippians 4:13', 'Hebrews 11:1',
    'James 1:5', 'Revelation 21:4',
]

# ----------------------------------------------------------------------
# Rule logic (matches errata exactly)
# ----------------------------------------------------------------------
PIVOT = re.compile(
    r"(?:That's not|This's not|It's not|That is not|This is not|It is not|"
    r"That was not|This was not|It was not).{0,50}?(?:It's|It is|It was)",
    re.IGNORECASE)

ENDORSE_PHRASES = [
    'the presenter agreed', 'the presenter endorsed', 'the presenter confirmed',
    'the presenter affirmed', 'the presenter accepted',
]


def pn(s):
    s = (s or '').strip()
    if not s:
        return None
    try:
        return float(s.lstrip('+'))
    except ValueError:
        return None


def is_true(s):
    return (s or '').strip().lower() == 'true'


def has_pivot(text):
    return bool(PIVOT.search(text or ''))


def has_endorsement(body):
    b = (body or '').lower()
    return any(ph in b for ph in ENDORSE_PHRASES)


def parse_citation(text):
    """Return (book, chapter, verse) where None means 'absent'."""
    text = (text or '').strip()
    if not text:
        return (None, None, None)
    # Book Chapter:Verse (optionally Verse-Verse2)
    m = re.match(r'^(.*?)\s+(\d+)\s*:\s*(\d+)(?:\s*-\s*\d+)?\s*$', text)
    if m:
        return (m.group(1).strip(), int(m.group(2)), int(m.group(3)))
    # Book Chapter
    m = re.match(r'^(.*?)\s+(\d+)\s*$', text)
    if m:
        return (m.group(1).strip(), int(m.group(2)), None)
    # Book only (single token or multiword, no trailing number)
    return (text.strip(), None, None)


def verse_in_range(verse, vr):
    vr = vr.strip()
    if '-' in vr:
        lo, hi = vr.split('-', 1)
        return int(lo) <= verse <= int(hi)
    return verse == int(vr)


def scripture_matches(text):
    """True if scripture_text matches a canonical entry in the registry."""
    book, chapter, verse = parse_citation(text)
    if book is None:
        return False  # empty / no book
    bl = book.lower()
    book_entries = [e for e in REGISTRY if e[0].lower() == bl]
    if not book_entries:
        return False  # book not in registry
    if chapter is None:
        return True  # book-only partial citation accepted
    ch_entries = [e for e in book_entries if e[1] == chapter]
    if not ch_entries:
        return False  # book+chapter not in registry
    if verse is None:
        return True  # book+chapter partial citation accepted
    return any(verse_in_range(verse, e[2]) for e in ch_entries)


def effective_minutes(timed, adj):
    """Apply the timing cap. timed/adj are floats (adj already last-wins)."""
    if timed is None:
        return None
    if timed == 0:
        return timed + adj  # cap does not apply (ratio undefined)
    if abs(adj) > 0.5 * abs(timed):
        return timed  # capped
    return timed + adj


def compute_finding(inv, clearance, retirement, air, timed, adj, band, speaker, scripture_text):
    # 1. Clearance -> ON_HOLD (stop)
    if clearance and clearance.strip().upper() == 'HOLD':
        return 'ON_HOLD'
    # 2. Retirement -> RETIRED
    if retirement and retirement.strip().upper() == 'RETIRED':
        return 'RETIRED'
    # 3. Air window -> OUT_OF_WINDOW
    if air and air.strip().lower() == 'false':
        return 'OUT_OF_WINDOW'
    # 4. Negation-pivot (with endorsement exception)
    ol = inv[6] if len(inv) > 6 else ''
    be = inv[7] if len(inv) > 7 else ''
    if has_pivot(ol) or has_pivot(be):
        sp = (speaker or '').strip().lower()
        exempt = (sp == 'third_party_testimony')
        if exempt and has_endorsement(be):
            exempt = False  # endorsement voids the exemption
        if not exempt:
            return 'NEGATION_PIVOT_USED'
    # 5. Scripture (with format check)
    hr = inv[3] if len(inv) > 3 else ''
    ci = inv[4] if len(inv) > 4 else ''
    if is_true(hr) and not is_true(ci):
        return 'UNCITED_SCRIPTURE_REF'
    if is_true(hr) and is_true(ci):
        if not scripture_matches(scripture_text):
            return 'UNCITED_SCRIPTURE_REF'
    # 6. Runtime (with cap)
    t = pn(timed)
    a = pn(adj) if adj not in (None, '') else 0.0
    if a is None:
        a = 0.0
    if t is not None:
        eff = effective_minutes(t, a)
        b = (band or '').strip().lower()
        if b in BANDS:
            lo, hi = BANDS[b]
            if eff < lo or eff > hi:
                return 'RUNTIME_OUT_OF_BAND'
    return 'none'


def numkey(s):
    m = re.search(r'\d+', s)
    return int(m.group()) if m else 0


# ----------------------------------------------------------------------
# Read existing inputs
# ----------------------------------------------------------------------
def read_rows_list(path):
    """Return list of raw rows (lists) preserving order, skipping header."""
    rows = []
    with path.open(encoding='utf-8') as f:
        for row in csv.reader(f):
            if not row:
                continue
            if row[0].strip().lower() == 'script_id':
                continue
            rows.append(row)
    return rows


def read_dict_lastwins(path, key='script_id', fields=None):
    d = {}
    with path.open(encoding='utf-8') as f:
        for row in csv.DictReader(f):
            sid = row.get(key, '').strip().upper()
            if sid:
                d[sid] = row
    return d


# inventory with last-wins (list form)
inv_rows_existing = read_rows_list(INPUT / 'script_inventory.csv')
inv_by_id = {}
for row in inv_rows_existing:
    sid = row[0].strip().upper()
    inv_by_id[sid] = row

clearance = read_dict_lastwins(INPUT / 'recording_clearance.csv')
retirement = read_dict_lastwins(INPUT / 'retirement_register.csv')
air = read_dict_lastwins(INPUT / 'air_window.csv')
timing = read_dict_lastwins(INPUT / 'timing_log.csv')
adj_dict = read_dict_lastwins(INPUT / 'timing_adjustments.csv')
band = read_dict_lastwins(INPUT / 'format_band.csv')
speaker = read_dict_lastwins(INPUT / 'speaker_attribution.csv')

print("Existing unique scripts:", len(inv_by_id))

# ----------------------------------------------------------------------
# Build scripture_text for existing inventory rows
# ----------------------------------------------------------------------
# Add scripture_text as the 9th column (index 8). For existing has_ref=true &
# cited=true scripts assign a valid citation so the new format check does not
# change their finding. Otherwise empty.
existing_inv_out = []
vc_iter = iter(VALID_CITATIONS * 100)
for row in inv_rows_existing:
    row = list(row)
    hr = row[3] if len(row) > 3 else ''
    ci = row[4] if len(row) > 4 else ''
    if is_true(hr) and is_true(ci):
        stext = next(vc_iter)
    else:
        stext = ''
    # pad to 8 columns if needed
    while len(row) < 8:
        row.append('')
    row.append(stext)
    existing_inv_out.append(row)
    # also refresh inv_by_id so compute uses the scripture_text
    inv_by_id[row[0].strip().upper()] = row

# ----------------------------------------------------------------------
# Define the 200 new scripts
# ----------------------------------------------------------------------
NEW = []  # list of dicts: sid, inv(list w/o scripture_text appended separately handled), spec


def add_script(sid, finding_expected, is_verbatim, uses_pivot, has_ref, cited,
               runtime_minutes, opening, body, scripture_text,
               clearance_status, retirement_status, in_window, timed, adj_rows,
               fmt_band, speech_source):
    NEW.append({
        'sid': sid,
        'expected': finding_expected,
        'is_verbatim': is_verbatim,
        'uses_pivot': uses_pivot,
        'has_ref': has_ref,
        'cited': cited,
        'runtime_minutes': runtime_minutes,
        'opening': opening,
        'body': body,
        'scripture_text': scripture_text,
        'clearance': clearance_status,
        'retirement': retirement_status,
        'in_window': in_window,
        'timed': timed,
        'adj_rows': adj_rows,  # list of adjustment strings (may be [] for none)
        'band': fmt_band,
        'speaker': speech_source,
    })


# Neutral text fragments (no pivot, no endorsement phrase)
NEUTRAL_OPEN = "We open with a calm pastoral note for the season ahead."
NEUTRAL_BODY = "Standard content with no unusual markers."
SCRIPTURE_OPEN = "We lean on a familiar promise as we plan the next season."
PIVOT_OPEN = "That's not a setback. It's a season of recalibration."

# ---- CHAIN 1: Scripture citation format (SC-2296..SC-2375, 80 scripts) ----
# All scripture scripts: CLEARED, in window, not retired, no pivot, timed=6 standard (in band).
cur = 2296

# Category 1: correct citations -> none (20)
correct_cites = [
    'Genesis 1:1', 'Exodus 20:3', 'Psalms 23:1', 'Psalms 91:1', 'Proverbs 3:5',
    'Isaiah 53:5', 'Matthew 5:3', 'Mark 16:6', 'Luke 15:4', 'John 3:16',
    'Acts 2:1', 'Romans 8:28', '1 Corinthians 13:1', '2 Corinthians 5:17',
    'Galatians 5:22', 'Ephesians 2:8', 'Philippians 4:13', 'Hebrews 11:1',
    'James 1:5', 'Revelation 21:4',
]
for c in correct_cites:
    add_script(f'SC-{cur}', 'none', 'False', 'False', 'True', 'True', 6,
               SCRIPTURE_OPEN, NEUTRAL_BODY, c, 'CLEARED', None, 'True', 6, [], 'standard', 'presenter')
    cur += 1

# Category 2: wrong verse -> UNCITED_SCRIPTURE_REF (20)
wrong_verse_cites = [
    'Genesis 1:99', 'Exodus 20:99', 'Psalms 23:99', 'Psalms 91:99', 'Proverbs 3:99',
    'Isaiah 53:99', 'Matthew 5:99', 'Mark 16:99', 'Luke 15:99', 'John 3:99',
    'Acts 2:99', 'Romans 8:99', '1 Corinthians 13:99', '2 Corinthians 5:99',
    'Galatians 5:99', 'Ephesians 2:99', 'Philippians 4:99', 'Hebrews 11:99',
    'James 1:99', 'Revelation 21:99',
]
for c in wrong_verse_cites:
    add_script(f'SC-{cur}', 'UNCITED_SCRIPTURE_REF', 'False', 'False', 'True', 'True', 6,
               SCRIPTURE_OPEN, NEUTRAL_BODY, c, 'CLEARED', None, 'True', 6, [], 'standard', 'presenter')
    cur += 1

# Category 3: case-variant book name -> none (10)
case_cites = [
    'GENESIS 1:1', 'exodus 20:3', 'PSALMS 23:1', 'psalms 91:1', 'PROVERBS 3:5',
    'ISAIAH 53:5', 'matthew 5:3', 'MARK 16:6', 'LUKE 15:4', 'JOHN 3:16',
]
for c in case_cites:
    add_script(f'SC-{cur}', 'none', 'False', 'False', 'True', 'True', 6,
               SCRIPTURE_OPEN, NEUTRAL_BODY, c, 'CLEARED', None, 'True', 6, [], 'standard', 'presenter')
    cur += 1

# Category 4: partial book+chapter / book-only -> none (10)
partial_cites = [
    'Genesis 1', 'Exodus 20', 'Psalms 23', 'Proverbs 3', 'Isaiah 53',
    'Matthew 5', 'John 3', 'Romans 8', 'Genesis', 'Psalms',
]
for c in partial_cites:
    add_script(f'SC-{cur}', 'none', 'False', 'False', 'True', 'True', 6,
               SCRIPTURE_OPEN, NEUTRAL_BODY, c, 'CLEARED', None, 'True', 6, [], 'standard', 'presenter')
    cur += 1

# Category 5: empty / garbage citation -> UNCITED_SCRIPTURE_REF (10)
garbage_cites = ['', '', '', '', '', 'xyz', 'not a citation', 'chapter seven', 'random words here', 'see notes']
for c in garbage_cites:
    add_script(f'SC-{cur}', 'UNCITED_SCRIPTURE_REF', 'False', 'False', 'True', 'True', 6,
               SCRIPTURE_OPEN, NEUTRAL_BODY, c, 'CLEARED', None, 'True', 6, [], 'standard', 'presenter')
    cur += 1

# Category 6: has_ref=true, cited=false -> UNCITED_SCRIPTURE_REF (10, no format check)
for _ in range(10):
    add_script(f'SC-{cur}', 'UNCITED_SCRIPTURE_REF', 'False', 'False', 'True', 'False', 6,
               SCRIPTURE_OPEN, NEUTRAL_BODY, '', 'CLEARED', None, 'True', 6, [], 'standard', 'presenter')
    cur += 1

assert cur == 2376, f"scripture chain end mismatch: {cur}"
print(f"Chain 1 (scripture): SC-2296..SC-{cur-1} ({cur-2296} scripts)")

# ---- CHAIN 2: Timing adjustment cap (SC-2376..SC-2435, 60 scripts) ----
# All timing scripts: CLEARED, in window, not retired, no pivot, no scripture (has_ref=False).
def tscript(sid, expected, timed, adj_rows, fmt_band):
    add_script(sid, expected, 'False', 'False', 'False', 'False', timed,
               NEUTRAL_OPEN, NEUTRAL_BODY, '', 'CLEARED', None, 'True', timed,
               adj_rows, fmt_band, 'presenter')

# Cat 1: within 50% cap -> use adjusted (15). |adj| strictly < 50% of timed.
within_50 = [
    (10, ['-3'], 'standard', 'none'),      # 30%, eff=7 IN
    (10, ['-4'], 'standard', 'none'),      # 40%, eff=6 IN
    (10, ['2'],  'extended', 'RUNTIME_OUT_OF_BAND'),  # 20%, eff=12 OUT
    (8,  ['-3'], 'standard', 'none'),      # 37.5%, eff=5 IN
    (8,  ['3'],  'extended', 'RUNTIME_OUT_OF_BAND'),  # 37.5%, eff=11 OUT
    (6,  ['-2'], 'standard', 'none'),      # 33.3%, eff=4 IN
    (6,  ['2'],  'standard', 'RUNTIME_OUT_OF_BAND'),  # 33.3%, eff=8 OUT
    (10, ['-1'], 'extended', 'none'),      # 10%, eff=9 IN
    (10, ['4'],  'standard', 'RUNTIME_OUT_OF_BAND'),  # 40%, eff=14 OUT
    (12, ['-5'], 'extended', 'none'),      # 41.7%, eff=7 IN
    (12, ['5'],  'extended', 'RUNTIME_OUT_OF_BAND'),  # 41.7%, eff=17 OUT
    (8,  ['-2'], 'standard', 'none'),      # 25%, eff=6 IN
    (8,  ['2'],  'standard', 'RUNTIME_OUT_OF_BAND'),  # 25%, eff=10 OUT
    (14, ['-6'], 'extended', 'none'),      # 42.9%, eff=8 IN
    (14, ['6'],  'extended', 'RUNTIME_OUT_OF_BAND'),  # 42.9%, eff=20 OUT
]
for (timed, adjs, bd, exp) in within_50:
    tscript(f'SC-{cur}', exp, timed, adjs, bd); cur += 1

# Cat 2: exceeding 50% cap -> use original timed (15). |adj| strictly > 50%.
exceed_50 = [
    # cap saves -> none (timed in band, capped eff=timed in band; uncapped would be OOB)
    (6, ['4'],  'standard', 'none'),     # 66.7%, capped 6 IN (uncapped 10 OUT)
    (7, ['4'],  'standard', 'none'),    # 57.1%, capped 7 IN (uncapped 11 OUT)
    (6, ['-4'], 'extended', 'none'),     # 66.7%, capped 6 IN (uncapped 2 OUT)
    (10, ['6'], 'extended', 'none'),     # 60%, capped 10 IN (uncapped 16 OUT)
    (7, ['-4'], 'extended', 'none'),     # 57.1%, capped 7 IN (uncapped 3 OUT)
    (5, ['3'],  'standard', 'none'),     # 60%, capped 5 IN (uncapped 8 OUT)
    (10, ['-6'], 'extended', 'none'),    # 60%, capped 10 IN (uncapped 4 OUT)
    (5, ['4'],  'standard', 'none'),     # 80%, capped 5 IN (uncapped 9 OUT)
    # cap pushes OOB -> RUNTIME (timed OOB, capped eff=timed OOB; uncapped would be IN)
    (9, ['-5'], 'standard', 'RUNTIME_OUT_OF_BAND'),  # 55.6%, capped 9 OUT (uncapped 4 IN)
    (11, ['-6'], 'standard', 'RUNTIME_OUT_OF_BAND'),  # 54.5%, capped 11 OUT (uncapped 5 IN)
    (3, ['2'],  'standard', 'RUNTIME_OUT_OF_BAND'),  # 66.7%, capped 3 OUT (uncapped 5 IN)
    (3, ['3'],  'standard', 'RUNTIME_OUT_OF_BAND'),  # 100%, capped 3 OUT (uncapped 6 IN)
    (11, ['-6'], 'extended', 'RUNTIME_OUT_OF_BAND'),  # 54.5%, capped 11 OUT (uncapped 5 IN)
    (5, ['4'],  'extended', 'RUNTIME_OUT_OF_BAND'),  # 80%, capped 5 OUT (uncapped 9 IN)
    (2, ['3'],  'standard', 'RUNTIME_OUT_OF_BAND'),  # 150%, capped 2 OUT (uncapped 5 IN)
]
for (timed, adjs, bd, exp) in exceed_50:
    tscript(f'SC-{cur}', exp, timed, adjs, bd); cur += 1

# Cat 3: exactly 50% -> NOT capped (5). |adj| == 50% of timed.
exact_50 = [
    (8, ['-4'], 'standard', 'none'),      # 50%, eff=4 IN
    (10, ['-5'], 'standard', 'none'),     # 50%, eff=5 IN
    (10, ['5'],  'standard', 'RUNTIME_OUT_OF_BAND'),  # 50%, eff=15 OUT
    (6, ['-3'], 'standard', 'RUNTIME_OUT_OF_BAND'),  # 50%, eff=3 OUT
    (8, ['4'],  'extended', 'RUNTIME_OUT_OF_BAND'),  # 50%, eff=12 OUT
]
for (timed, adjs, bd, exp) in exact_50:
    tscript(f'SC-{cur}', exp, timed, adjs, bd); cur += 1

# Cat 4: timed=0 -> cap doesn't apply (5). effective = 0 + adj.
timed_zero = [
    (0, ['6'],  'standard', 'none'),      # eff=6 IN
    (0, ['10'], 'extended', 'none'),     # eff=10 IN
    (0, ['3'],  'standard', 'RUNTIME_OUT_OF_BAND'),  # eff=3 OUT
    (0, ['11'], 'extended', 'RUNTIME_OUT_OF_BAND'),  # eff=11 OUT
    (0, ['7'],  'standard', 'none'),      # eff=7 IN
]
for (timed, adjs, bd, exp) in timed_zero:
    tscript(f'SC-{cur}', exp, timed, adjs, bd); cur += 1

# Cat 5: multiple adjustments, last-wins exceeds 50% cap (10).
multi_adj = [
    (6, ['0', '4'],  'standard', 'none'),     # last=4 66.7%, capped 6 IN
    (7, ['0', '4'],  'standard', 'none'),     # last=4 57.1%, capped 7 IN
    (6, ['0', '-4'], 'extended', 'none'),     # last=-4 66.7%, capped 6 IN
    (9, ['0', '-5'], 'standard', 'RUNTIME_OUT_OF_BAND'),  # last=-5 55.6%, capped 9 OUT
    (11, ['0', '-6'], 'extended', 'RUNTIME_OUT_OF_BAND'),  # last=-6 54.5%, capped 11 OUT
    (3, ['0', '2'],  'standard', 'RUNTIME_OUT_OF_BAND'),  # last=2 66.7%, capped 3 OUT
    (5, ['0', '3'],  'standard', 'none'),     # last=3 60%, capped 5 IN
    (10, ['0', '6'], 'extended', 'none'),     # last=6 60%, capped 10 IN
    (2, ['0', '3'],  'standard', 'RUNTIME_OUT_OF_BAND'),  # last=3 150%, capped 2 OUT
    (5, ['0', '4'],  'extended', 'RUNTIME_OUT_OF_BAND'),  # last=4 80%, capped 5 OUT
]
for (timed, adjs, bd, exp) in multi_adj:
    tscript(f'SC-{cur}', exp, timed, adjs, bd); cur += 1

# Cat 6: negative adjustments exceeding 50% (10). All adj < 0, |adj| > 50%.
neg_adj = [
    (6, ['-4'],  'standard', 'none'),     # 66.7%, capped 6 IN
    (7, ['-4'],  'standard', 'none'),     # 57.1%, capped 7 IN
    (10, ['-6'], 'extended', 'none'),     # 60%, capped 10 IN
    (7, ['-4'],  'extended', 'none'),     # 57.1%, capped 7 IN
    (6, ['-4'],  'extended', 'none'),     # 66.7%, capped 6 IN
    (9, ['-5'],  'standard', 'RUNTIME_OUT_OF_BAND'),  # 55.6%, capped 9 OUT
    (11, ['-6'], 'standard', 'RUNTIME_OUT_OF_BAND'),  # 54.5%, capped 11 OUT
    (11, ['-7'], 'extended', 'RUNTIME_OUT_OF_BAND'),  # 63.6%, capped 11 OUT
    (10, ['-6'], 'standard', 'RUNTIME_OUT_OF_BAND'),  # 60%, capped 10 OUT
    (9, ['-5'],  'extended', 'none'),     # 55.6%, capped 9 IN
]
for (timed, adjs, bd, exp) in neg_adj:
    tscript(f'SC-{cur}', exp, timed, adjs, bd); cur += 1

assert cur == 2436, f"timing chain end mismatch: {cur}"
print(f"Chain 2 (timing cap): SC-2376..SC-{cur-1} ({cur-2376} scripts)")

# ---- CHAIN 3: Presenter endorsement exception (SC-2436..SC-2495, 60 scripts) ----
# All endorsement scripts: CLEARED, in window, not retired, has_ref=False, timed=6 standard (in band).
endorse_bodies = {
    'agreed':    "The presenter agreed with the guest voice on every detail of the testimony.",
    'endorsed':  "The presenter endorsed the third-party account as the official position.",
    'confirmed': "The presenter confirmed the guest testimony as accurate for the record.",
    'affirmed':  "The presenter affirmed the witness statement before the board reviewed it.",
    'accepted':  "The presenter accepted the visitor account as the team's working summary.",
}

# Cat 1: third-party + pivot + NO endorsement -> exempt -> none (15)
for _ in range(15):
    add_script(f'SC-{cur}', 'none', 'True', 'True', 'False', 'False', 6,
               PIVOT_OPEN, NEUTRAL_BODY, '', 'CLEARED', None, 'True', 6, [], 'standard', 'third_party_testimony')
    cur += 1

# Cat 2: third-party + pivot + "the presenter agreed" -> NEGATION_PIVOT_USED (15)
for _ in range(15):
    add_script(f'SC-{cur}', 'NEGATION_PIVOT_USED', 'True', 'True', 'False', 'False', 6,
               PIVOT_OPEN, endorse_bodies['agreed'], '', 'CLEARED', None, 'True', 6, [], 'standard', 'third_party_testimony')
    cur += 1

# Cat 3: third-party + pivot + "the presenter endorsed" -> NEGATION_PIVOT_USED (10)
for _ in range(10):
    add_script(f'SC-{cur}', 'NEGATION_PIVOT_USED', 'True', 'True', 'False', 'False', 6,
               PIVOT_OPEN, endorse_bodies['endorsed'], '', 'CLEARED', None, 'True', 6, [], 'standard', 'third_party_testimony')
    cur += 1

# Cat 4: third-party + pivot + confirmed/affirmed/accepted -> NEGATION_PIVOT_USED (10)
for ph in (['confirmed', 'affirmed', 'accepted', 'confirmed', 'affirmed',
            'accepted', 'confirmed', 'affirmed', 'accepted', 'confirmed']):
    add_script(f'SC-{cur}', 'NEGATION_PIVOT_USED', 'True', 'True', 'False', 'False', 6,
               PIVOT_OPEN, endorse_bodies[ph], '', 'CLEARED', None, 'True', 6, [], 'standard', 'third_party_testimony')
    cur += 1

# Cat 5: third-party + NO pivot + endorsement -> none (5)
for ph in (['agreed', 'endorsed', 'confirmed', 'affirmed', 'accepted']):
    add_script(f'SC-{cur}', 'none', 'True', 'False', 'False', 'False', 6,
               NEUTRAL_OPEN, endorse_bodies[ph], '', 'CLEARED', None, 'True', 6, [], 'standard', 'third_party_testimony')
    cur += 1

# Cat 6: presenter + pivot + no endorsement -> NEGATION_PIVOT_USED (5)
for _ in range(5):
    add_script(f'SC-{cur}', 'NEGATION_PIVOT_USED', 'False', 'True', 'False', 'False', 6,
               PIVOT_OPEN, NEUTRAL_BODY, '', 'CLEARED', None, 'True', 6, [], 'standard', 'presenter')
    cur += 1

assert cur == 2496, f"endorsement chain end mismatch: {cur}"
print(f"Chain 3 (endorsement): SC-2436..SC-{cur-1} ({cur-2436} scripts)")
print(f"Total new scripts: {len(NEW)}")

# ----------------------------------------------------------------------
# Compute findings for the 200 new scripts and assert they match expectations
# ----------------------------------------------------------------------
for s in NEW:
    inv = [s['sid'], s['is_verbatim'], s['uses_pivot'], s['has_ref'], s['cited'],
           str(s['runtime_minutes']), s['opening'], s['body']]
    # adj: last-wins
    adj_rows = s['adj_rows']
    adj_val = adj_rows[-1] if adj_rows else ''
    finding = compute_finding(inv, s['clearance'], s['retirement'], s['in_window'],
                              str(s['timed']), adj_val, s['band'], s['speaker'], s['scripture_text'])
    if finding != s['expected']:
        raise SystemExit(f"ASSERT FAIL {s['sid']}: computed={finding} expected={s['expected']} "
                         f"timed={s['timed']} adj={adj_val} band={s['band']} sp={s['speaker']} "
                         f"stext={s['scripture_text']!r}")
print("All 200 new scripts: computed finding matches expected. OK")

# ----------------------------------------------------------------------
# Add new scripts to in-memory input stores (last-wins) and compute full golden
# ----------------------------------------------------------------------
# Register new rows in the lookup dicts so the full recompute sees them.
for s in NEW:
    sid = s['sid'].upper()
    # inventory (with scripture_text appended)
    inv_row = [s['sid'], s['is_verbatim'], s['uses_pivot'], s['has_ref'], s['cited'],
               str(s['runtime_minutes']), s['opening'], s['body'], s['scripture_text']]
    inv_by_id[sid] = inv_row
    clearance[sid] = {'script_id': s['sid'], 'clearance_status': s['clearance']}
    if s['retirement'] is not None:
        retirement[sid] = {'script_id': s['sid'], 'status': s['retirement']}
    air[sid] = {'script_id': s['sid'], 'in_window': s['in_window']}
    timing[sid] = {'script_id': s['sid'], 'timed_minutes': str(s['timed'])}
    if s['adj_rows']:
        # last-wins: overwrite with the last value
        adj_dict[sid] = {'script_id': s['sid'], 'adjustment_minutes': s['adj_rows'][-1]}
    band[sid] = {'script_id': s['sid'], 'band': s['band']}
    speaker[sid] = {'script_id': s['sid'], 'speech_source': s['speaker']}

all_sids = sorted(inv_by_id.keys(), key=numkey)
print("Total unique scripts (existing + new):", len(all_sids))

# ----------------------------------------------------------------------
# Compute the FULL golden with ALL rules (old + new)
# ----------------------------------------------------------------------
gold = {}
changed_existing = []
for sid in all_sids:
    inv = inv_by_id[sid]
    cl = clearance.get(sid, {}).get('clearance_status', '')
    ret = retirement.get(sid, {}).get('status', '')
    aw = air.get(sid, {}).get('in_window', '')
    tm = timing.get(sid, {}).get('timed_minutes', '')
    ad = adj_dict.get(sid, {}).get('adjustment_minutes', '')
    bd = band.get(sid, {}).get('band', '')
    sp = speaker.get(sid, {}).get('speech_source', '')
    stext = inv[8] if len(inv) > 8 else ''
    f = compute_finding(inv, cl, ret, aw, tm, ad, bd, sp, stext)
    gold[sid] = f

# Compare with the OLD golden to report what changed among existing scripts
old_gold = {}
with (SOL / 'script_style_audit.csv').open(encoding='utf-8') as f:
    for row in csv.DictReader(f):
        old_gold[row['script_id'].strip().upper()] = row['finding'].strip()

for sid in sorted(old_gold.keys(), key=numkey):
    if gold.get(sid) != old_gold.get(sid):
        changed_existing.append((sid, old_gold.get(sid), gold.get(sid)))

print(f"Existing scripts whose finding changed (timing cap): {len(changed_existing)}")
for c in changed_existing:
    print("   ", c)

# ----------------------------------------------------------------------
# Write scripture_registry.csv
# ----------------------------------------------------------------------
reg_path = INPUT / 'scripture_registry.csv'
with reg_path.open('w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['book', 'chapter', 'verse_range', 'canonical_form'])
    for e in REGISTRY:
        w.writerow(list(e))
print("Wrote scripture_registry.csv (%d entries)" % len(REGISTRY))

# ----------------------------------------------------------------------
# Rewrite script_inventory.csv with the scripture_text column (existing + new)
# ----------------------------------------------------------------------
inv_path = INPUT / 'script_inventory.csv'
with inv_path.open('w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['script_id', 'is_verbatim_testimony', 'uses_negation_pivot',
                'has_scripture_ref', 'scripture_cited', 'runtime_minutes',
                'opening_line', 'body_excerpt', 'scripture_text'])
    # existing rows (in original order) with scripture_text appended
    written_sids = set()
    for row in existing_inv_out:
        w.writerow(row)
        written_sids.add(row[0].strip().upper())
    # new rows
    for s in NEW:
        w.writerow([s['sid'], s['is_verbatim'], s['uses_pivot'], s['has_ref'], s['cited'],
                    str(s['runtime_minutes']), s['opening'], s['body'], s['scripture_text']])
print("Rewrote script_inventory.csv with scripture_text column")

# ----------------------------------------------------------------------
# Append new rows to the other input CSVs
# ----------------------------------------------------------------------
def append_rows(path, header, new_data_rows):
    """new_data_rows: list of lists (without header)."""
    with path.open('a', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        for r in new_data_rows:
            w.writerow(r)

# recording_clearance
clr_rows = []
for s in NEW:
    clr_rows.append([s['sid'], s['clearance']])
append_rows(INPUT / 'recording_clearance.csv', None, clr_rows)

# air_window
aw_rows = [[s['sid'], s['in_window']] for s in NEW]
append_rows(INPUT / 'air_window.csv', None, aw_rows)

# timing_log
tl_rows = [[s['sid'], str(s['timed'])] for s in NEW]
append_rows(INPUT / 'timing_log.csv', None, tl_rows)

# timing_adjustments (only scripts that have adjustment rows)
ta_rows = []
for s in NEW:
    for a in s['adj_rows']:
        ta_rows.append([s['sid'], a])
append_rows(INPUT / 'timing_adjustments.csv', None, ta_rows)

# format_band
fb_rows = [[s['sid'], s['band']] for s in NEW]
append_rows(INPUT / 'format_band.csv', None, fb_rows)

# speaker_attribution
sa_rows = [[s['sid'], s['speaker']] for s in NEW]
append_rows(INPUT / 'speaker_attribution.csv', None, sa_rows)

# retirement_register: none of the new scripts are retired, so nothing to append
print("Appended new rows to clearance/air/timing/band/speaker CSVs")

# ----------------------------------------------------------------------
# Write golden audit CSV
# ----------------------------------------------------------------------
audit_path = SOL / 'script_style_audit.csv'
with audit_path.open('w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['script_id', 'finding'])
    for sid in all_sids:
        w.writerow([sid, gold[sid]])
print("Wrote golden script_style_audit.csv (%d rows)" % len(all_sids))

# ----------------------------------------------------------------------
# Compute results.json
# ----------------------------------------------------------------------
cleared = {sid for sid in all_sids
           if clearance.get(sid, {}).get('clearance_status', '').strip().upper() == 'CLEARED'}
results = {
    'script_count': len(cleared),
    'flagged_count': sum(1 for v in gold.values() if v != 'none'),
    'negation_pivot_count': sum(1 for v in gold.values() if v == 'NEGATION_PIVOT_USED'),
    'uncited_scripture_count': sum(1 for v in gold.values() if v == 'UNCITED_SCRIPTURE_REF'),
    'runtime_breach_count': sum(1 for v in gold.values() if v == 'RUNTIME_OUT_OF_BAND'),
}
(SOL / 'results.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
print("results.json:", json.dumps(results))

# breakdown of new scripts
new_findings = Counter(gold[s['sid'].upper()] for s in NEW)
print("New scripts finding breakdown:", dict(new_findings))

# ----------------------------------------------------------------------
# Write golden memo
# ----------------------------------------------------------------------
memo = []
memo.append(f"# Leadership brief style audit — {len(all_sids)} scripts")
memo.append("")
memo.append(f"{len(all_sids)} logged scripts were checked against the communications style "
            f"guide and policy errata v4. {sum(1 for v in gold.values() if v == 'none')} rows are "
            f"compliant; {sum(1 for v in gold.values() if v != 'none')} carry a finding.")
memo.append("")
memo.append("## Finding categories")
memo.append("")
memo.append("Each script receives exactly one finding under the priority chain "
            "`ON_HOLD` > `RETIRED` > `OUT_OF_WINDOW` > `NEGATION_PIVOT_USED` > "
            "`UNCITED_SCRIPTURE_REF` > `RUNTIME_OUT_OF_BAND` > `none`.")
memo.append("")
for finding in ['ON_HOLD', 'RETIRED', 'OUT_OF_WINDOW', 'NEGATION_PIVOT_USED',
                'UNCITED_SCRIPTURE_REF', 'RUNTIME_OUT_OF_BAND']:
    scripts = [sid for sid, f in gold.items() if f == finding]
    memo.append(f"- **{finding}** — {len(scripts)} scripts.")
memo.append(f"- **none** — {sum(1 for v in gold.values() if v == 'none')} scripts (compliant).")
memo.append("")
memo.append("## Testimony exemption and the endorsement exception")
memo.append("")
memo.append("The negation-pivot rule exempts scripts whose speaker attribution is "
            "`third_party_testimony`; this exemption applies only to the negation-pivot "
            "rule, not to scripture or runtime checks. The presenter endorsement "
            "exception voids that exemption: when a third-party testimony script's "
            "`body_excerpt` contains any of the phrases 'the presenter agreed', "
            "'the presenter endorsed', 'the presenter confirmed', 'the presenter "
            "affirmed', or 'the presenter accepted' (case-insensitive), the testimony is "
            "treated as the presenter's own position and the negation-pivot check applies "
            "normally. This is why some third_party_testimony scripts still receive "
            "`NEGATION_PIVOT_USED`.")
memo.append("")
memo.append("## Scripture citation format")
memo.append("")
memo.append("When `has_scripture_ref` is true and `scripture_cited` is true, the citation "
            "in `scripture_text` must match a canonical entry in `scripture_registry.csv`. "
            "Book names match case-insensitively; partial citations (book only, or "
            "book+chapter) are accepted when the book or book+chapter appears in the "
            "registry. A full `Book Chapter:Verse` citation is accepted only when the verse "
            "falls within the registry's `verse_range` for that book and chapter. A "
            "citation that references a book, chapter, or verse not in the registry is "
            "`UNCITED_SCRIPTURE_REF`. When `has_scripture_ref` is true but "
            "`scripture_cited` is not true, the finding is also `UNCITED_SCRIPTURE_REF` "
            "(no format check is needed).")
memo.append("")
memo.append("## Timing adjustment cap")
memo.append("")
memo.append("Effective minutes normally equal `timing_log.timed_minutes` plus the winning "
            "`timing_adjustments.adjustment_minutes` (last row wins). The timing cap "
            "limits a single adjustment: when the absolute adjustment exceeds 50% of the "
            "original timed minutes, the adjustment is capped and effective minutes equal "
            "the original timed minutes. An adjustment of exactly 50% is not capped. When "
            "timed minutes is 0 the cap does not apply. The cap is applied after last-wins "
            "resolution and before the band boundary comparison in `band_definition.csv` "
            "(active rows only, latest effective_date wins). A script outside its band "
            "receives `RUNTIME_OUT_OF_BAND`.")
memo.append("")
memo.append("## results.json figures")
memo.append("")
memo.append(f"- `script_count` = {results['script_count']} (winning clearance CLEARED).")
memo.append(f"- `flagged_count` = {results['flagged_count']}.")
memo.append(f"- `negation_pivot_count` = {results['negation_pivot_count']}.")
memo.append(f"- `uncited_scripture_count` = {results['uncited_scripture_count']}.")
memo.append(f"- `runtime_breach_count` = {results['runtime_breach_count']}.")
memo.append("")
memo_text = '\n'.join(memo)
(SOL / 'style_audit_memo.md').write_text(memo_text, encoding='utf-8')
print(f"Wrote golden memo ({len(memo_text)} chars)")

# ----------------------------------------------------------------------
# Rebuild verifier.json
# ----------------------------------------------------------------------
vj = json.loads(VERIFIER.read_text(encoding='utf-8'))
# Keep the first 16 structural checks (file existence, memo content, results_exists,
# no_pipe_joins, audit_header_exact, no_duplicate_script_ids). Remove per-script,
# audit_exactly_n_rows, and result_* checks.
keep = []
for v in vj['verifiers']:
    nm = v['name']
    if re.match(r'^sc\d+$', nm):
        continue
    if nm == 'audit_exactly_n_rows':
        continue
    if nm.startswith('result_'):
        continue
    keep.append(v)
print(f"Keeping {len(keep)} structural checks")

n = len(all_sids)
# Add per-script checks
for sid in all_sids:
    idx = numkey(sid)
    finding = gold[sid]
    keep.append({
        'name': 'sc%d' % idx,
        'metadata': {'how_justification': 'Per-script finding check.',
                     'why_justification': 'Script finding must be correct.'},
        'source': {'type': 'file', 'file': {'type': 'csv', 'command': 'extract_text',
                    'arguments': {'path': 'script_style_audit.csv'}}},
        'assertion': {'type': 'deterministic',
                      'expected': r'(?mi)^\x22?%s\x22?\s*,\s*\x22?%s\x22?\s*\r?$' % (re.escape(sid), re.escape(finding)),
                      'deterministic': {'path': '$.text', 'comparison': 'regex_match'}}
    })
# audit_exactly_n_rows
keep.append({
    'name': 'audit_exactly_n_rows',
    'metadata': {'how_justification': f'Checks script_style_audit.csv has one header and exactly {n} data rows.',
                 'why_justification': f'Audit must cover every unique script ({n} rows).'},
    'source': {'type': 'file', 'file': {'type': 'csv', 'command': 'extract_text',
                'arguments': {'path': 'script_style_audit.csv'}}},
    'assertion': {'type': 'deterministic',
                  'expected': r'(?is)^(?:[^\r\n]*\r?\n){%d}[^\r\n]+\r?\n?$' % n,
                  'deterministic': {'path': '$.text', 'comparison': 'regex_match'}}
})
# result checks
for name, path, expected in [
    ('result_script_count', '$.script_count', results['script_count']),
    ('result_flagged_count', '$.flagged_count', results['flagged_count']),
    ('result_negation_pivot_count', '$.negation_pivot_count', results['negation_pivot_count']),
    ('result_uncited_scripture_count', '$.uncited_scripture_count', results['uncited_scripture_count']),
    ('result_runtime_breach_count', '$.runtime_breach_count', results['runtime_breach_count']),
]:
    keep.append({
        'name': name,
        'metadata': {'how_justification': f'Reads results.json and compares {path} to {expected}.',
                     'why_justification': f'Derived figure {name.replace("result_", "")}={expected}.'},
        'source': {'type': 'file', 'file': {'type': 'json', 'command': 'read_file',
                    'arguments': {'path': 'results.json'}}},
        'assertion': {'type': 'deterministic', 'expected': expected,
                      'deterministic': {'path': path, 'comparison': 'equals'}}
    })

vj['verifiers'] = keep
VERIFIER.write_text(json.dumps(vj, indent=4) + '\n', encoding='utf-8')
print(f"Rebuilt verifier.json: {len(keep)} checks (per-script={n}, +1 rows, +5 results, +{len(keep)-n-6} structural)")

# ----------------------------------------------------------------------
# Update instruction.md
# ----------------------------------------------------------------------
INSTRUCTION = """# Task

Before these leadership-brief scripts get recorded, audit the attached inputs under `input/` against the internal communications style guide and the current policy errata (ignore obsolete errata and informal ops notes; honor trim, last-wins, and token rules stated in the authoritative errata): recording clearance, retirement, air window, negation-pivot rhetoric, scripture citation (including the scripture citation format check against `scripture_registry.csv`), and runtime band (including the timing adjustment cap). Third-party testimony is handled differently from the presenter's own material: the negation-pivot testimony exemption is voided when the presenter endorses the testimony (see the presenter endorsement exception in the errata). The audit covers every script in `script_inventory.csv` (2422 scripts). Save `script_style_audit.csv` with header `script_id,finding` and one row per script, reporting each `script_id` in its canonical upper-cased `SC-NN` form (trim and uppercase the inventory id), and a single `finding` value (`ON_HOLD`, `RETIRED`, `OUT_OF_WINDOW`, `NEGATION_PIVOT_USED`, `UNCITED_SCRIPTURE_REF`, `RUNTIME_OUT_OF_BAND`, `none`). Then write `style_audit_memo.md` (at least 800 characters) explaining each finding and how the testimony exemption applies; the memo must name each finding category (`ON_HOLD`, `RETIRED`, `OUT_OF_WINDOW`, `NEGATION_PIVOT_USED`, `UNCITED_SCRIPTURE_REF`, `RUNTIME_OUT_OF_BAND`, `none`) and the concepts `testimony`, `exemption`, and `third_party_testimony`.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `script_style_audit.csv` — Per-script style audit
    - `style_audit_memo.md` — Markdown memo
    - `results.json` — a JSON object with the keys `script_count` (errata v4 takes precedence for all count definitions; script_count counts all scripts whose winning clearance is CLEARED regardless of other findings), `flagged_count` (scripts with a finding other than `none`), `negation_pivot_count`, `uncited_scripture_count`, `runtime_breach_count`
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.
"""
(TASK / 'instruction.md').write_text(INSTRUCTION, encoding='utf-8')
print("Updated instruction.md (2422 scripts, new rules mentioned)")

# ----------------------------------------------------------------------
# Update policy_errata_v4.md
# ----------------------------------------------------------------------
errata = (INPUT / 'policy_errata_v4.md').read_text(encoding='utf-8')

# Add the endorsement exception to the Negation-pivot section (after the Exemption paragraph).
endorse_addition = """

**Presenter endorsement exception.** The third-party testimony exemption from the
negation-pivot check (see above) applies ONLY when the presenter did NOT endorse the
testimony. If the script's `body_excerpt` contains any of the phrases 'the presenter
agreed', 'the presenter endorsed', 'the presenter confirmed', 'the presenter affirmed',
or 'the presenter accepted' (case-insensitive), the exemption is voided and the
negation-pivot check applies normally, even for third-party testimony speakers. This
is because an endorsement makes the testimony the presenter's own position."""

# Insert after the Exemption paragraph (which ends before "## Scripture citations")
errata = errata.replace(
    "## Scripture citations",
    endorse_addition + "\n## Scripture citations", 1)

# Add the scripture format sub-rule to the Scripture citations section.
scripture_old = """## Scripture citations

Treat `has_scripture_ref` / `scripture_cited` as true **only** when the trimmed value is
exactly `true` (case-insensitive). Tokens such as `yes`, `1`, `Y`, or `TRUE` with extra
characters are **not** true. If `has_scripture_ref` is true and `scripture_cited` is not
true -> `UNCITED_SCRIPTURE_REF`."""

scripture_new = """## Scripture citations

Treat `has_scripture_ref` / `scripture_cited` as true **only** when the trimmed value is
exactly `true` (case-insensitive). Tokens such as `yes`, `1`, `Y`, or `TRUE` with extra
characters are **not** true. If `has_scripture_ref` is true and `scripture_cited` is not
true -> `UNCITED_SCRIPTURE_REF`.

**Scripture citation format.** When a script's `has_scripture_ref` is `true` AND
`scripture_cited` is `true`, the citation text in the inventory's `scripture_text`
column must match a canonical entry in `scripture_registry.csv` (columns
`book,chapter,verse_range,canonical_form`). Parse `scripture_text` as `Book`,
`Book Chapter`, or `Book Chapter:Verse` (the book is everything before the last
integer chapter number; chapter and verse are integers). Book names are matched
case-insensitively. A citation that references a book, chapter, or verse NOT in the
registry is treated as `UNCITED_SCRIPTURE_REF` (the reference exists but is not a
recognized canonical citation). For a full `Book Chapter:Verse` citation, the verse
must fall within the `verse_range` of a registry entry whose book (case-insensitive)
and chapter match. Partial citations (`Book` only, or `Book Chapter` without a verse)
are accepted if the book (or book+chapter) appears in the registry. An empty or
unparseable `scripture_text` is treated as not matching (`UNCITED_SCRIPTURE_REF`).

Example: timed=10, last adjustment=-8 (80% of 10 > 50%) -> effective=10 (capped), not 2.
timed=10, last adjustment=-4 (40% <= 50%) -> effective=6 (not capped)."""

errata = errata.replace(scripture_old, scripture_new, 1)

# Hmm, the "Example: timed..." belongs to the timing cap, not scripture. Fix: move it.
errata = errata.replace(
    "Example: timed=10, last adjustment=-8 (80% of 10 > 50%) -> effective=10 (capped), not 2.\ntimed=10, last adjustment=-4 (40% <= 50%) -> effective=6 (not capped).",
    "", 1)

# Add the timing cap to the Runtime bands section (after the effective minutes paragraph).
runtime_old = """Effective minutes = `timing_log.timed_minutes` + winning
`timing_adjustments.adjustment_minutes` (missing adjustment -> 0)."""

runtime_new = """Effective minutes = `timing_log.timed_minutes` + winning
`timing_adjustments.adjustment_minutes` (missing adjustment -> 0).

**Timing adjustment cap.** When computing effective minutes, if the absolute value of
the timing adjustment exceeds 50% of the original timed minutes from `timing_log.csv`,
the adjustment is "capped": the effective minutes are calculated as `timed_minutes`
(ignoring the adjustment). This prevents a single adjustment from swinging a script's
runtime by more than half its original value. An adjustment whose absolute value is
exactly 50% of timed minutes is **not** capped (the cap requires strictly more than
50%). When `timed_minutes` is 0 the cap does **not** apply (the ratio is undefined) and
effective minutes = `timed_minutes` + adjustment. The cap applies AFTER last-wins
resolution but BEFORE band boundary comparison.
Example: timed=10, last adjustment=-8 (80% of 10 > 50%) -> effective=10 (capped), not 2.
timed=10, last adjustment=-4 (40% <= 50%) -> effective=6 (not capped)."""

errata = errata.replace(runtime_old, runtime_new, 1)

(INPUT / 'policy_errata_v4.md').write_text(errata, encoding='utf-8')
print("Updated policy_errata_v4.md (3 new sub-rules added)")

# ----------------------------------------------------------------------
# Update README.md
# ----------------------------------------------------------------------
readme = (TASK / 'README.md').read_text(encoding='utf-8')
readme = readme.replace(
    "input/script_inventory.csv — 2222 scripts with opening_line and body_excerpt",
    "input/script_inventory.csv — 2422 scripts with opening_line, body_excerpt and scripture_text")
readme = readme.replace(
    "- input/speaker_attribution.csv — speech source per script\n",
    "- input/speaker_attribution.csv — speech source per script\n- input/scripture_registry.csv — canonical scripture citations (book,chapter,verse_range,canonical_form)\n")
readme = readme.replace(
    "2044+200 deterministic checks (2244):",
    f"{len(keep)-22}+22 deterministic checks ({len(keep)}):")
readme = readme.replace(
    "The 200 added fair-hurdle scripts (SC-2096..SC-2295) exercise derivable edge cases at scale: complex timing adjustments (last-wins vs sum, exact band boundaries, negative effective minutes), multi-rule priority interactions (ON_HOLD > RETIRED > OUT_OF_WINDOW > NEGATION_PIVOT_USED > UNCITED_SCRIPTURE_REF > RUNTIME_OUT_OF_BAND, including triple/quadruple overlaps and PENDING-continues cases), clarified negation-pivot rules (same-pronoun restatements, `was not` vs `wasn't`/`isn't` contractions, `It`-in-second-clause requirement, separators, case-insensitivity, testimony exemption, pivot in body_excerpt), scripture exactly-true token edge cases, and clearance last-wins flips (CLEARED/HOLD/PENDING ordering).",
    f"The 200 added fair-hurdle scripts (SC-2096..SC-2295) exercise derivable edge cases at scale: complex timing adjustments (last-wins vs sum, exact band boundaries, negative effective minutes), multi-rule priority interactions (ON_HOLD > RETIRED > OUT_OF_WINDOW > NEGATION_PIVOT_USED > UNCITED_SCRIPTURE_REF > RUNTIME_OUT_OF_BAND, including triple/quadruple overlaps and PENDING-continues cases), clarified negation-pivot rules (same-pronoun restatements, `was not` vs `wasn't`/`isn't` contractions, `It`-in-second-clause requirement, separators, case-insensitivity, testimony exemption, pivot in body_excerpt), scripture exactly-true token edge cases, and clearance last-wins flips (CLEARED/HOLD/PENDING ordering). A further 200 multi-step reasoning scripts (SC-2296..SC-2495) add three cross-file chains: scripture citation format validation against scripture_registry.csv (book/chapter/verse-range matching, partial citations, case-insensitive book names, empty/garbage citations, the cited=false path), the timing adjustment cap (|adjustment| > 50% of timed minutes caps effective minutes to timed_minutes; exactly-50% and timed=0 edge cases; last-wins interactions; negative adjustments), and the presenter endorsement exception (endorsement phrases in body_excerpt void the third_party_testimony negation-pivot exemption). These are sub-checks of existing finding codes, so no new finding codes are introduced.")
(TASK / 'README.md').write_text(readme, encoding='utf-8')
print("Updated README.md")

print("\n=== GENERATION COMPLETE ===")
print(f"Total scripts: {len(all_sids)}")
print(f"Total verifier checks: {len(keep)}")
print(f"results.json: {json.dumps(results)}")
print(f"Existing scripts changed by timing cap: {len(changed_existing)}")
