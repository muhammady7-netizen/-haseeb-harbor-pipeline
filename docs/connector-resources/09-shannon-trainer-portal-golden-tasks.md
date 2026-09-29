# Shannon Trainer Portal + Golden Tasks

**Source:** https://script.google.com/a/macros/turing.com/s/AKfycbxyMRTfRUJcEnm33v7yzgDWpQH8txjoZ1sYiEsk3wFAlDfZVvo5M0lzYz8kLql7CKUymA/exec
**Developer:** Md Hussain (md.h1@turing.com)

## Trainer Workflow (6 steps)

1. **Claim a Task** — tracker sheet → find unclaimed task → assign via Task System
2. **Trainer Guides** — follow connector task doc + guides
3. **Upload Completed Task** — Google Drive folder / Batch_no
4. **Generate review.csv** — format sheet + detailed info + generator tool
5. **QC Tool — Final Check** — Shannon QC Control V2 → upload → check → fix if fail
6. **Report Bugs/Issues** — Harbor QC Parking Lot

## All Portal Links

| Resource | URL |
|---|---|
| Connector Task Guidelines | https://docs.google.com/document/d/1jdmYao4I8HQdHZikLu2PmPz1Ye_JJC9EBpW2YfR-TgM/edit?tab=t.0 |
| New Documentation | https://docs.google.com/document/d/1rbyXaBe-rXQdFHrfR_gs5whLRg_FVYBtsgqRjeGaJpU/edit?tab=t.myl3fl1jbi03 |
| Trainer Guide 1 | https://docs.google.com/document/d/14Lk44mmisI2V007uRljtzOa8P8gPqgnyv5fE4ZEs-Zc/edit?tab=t.0 |
| Trainer Guide 2 | https://docs.google.com/document/d/1pu_PVh8L3ped-pS9cn8M5eXx6zs7cXlIfs0Km-Zgi5Q/edit?tab=t.0 |
| Cheat Sheet Guide | https://docs.google.com/document/d/1zecue6jbiDz4jLdNNHIKVdt68sWXMoQIo-ZJDY6Nm9E/edit?tab=t.0 |
| Upload Task (Drive) | https://drive.google.com/drive/folders/15ULnjl1MvMNdkqLlz9wLXpxDiZzM1bDW |
| review.csv Format | https://docs.google.com/spreadsheets/d/1bzSP9mrqEZzZEC92SuPvpynLiWAFyks-vPA6OzGJZys/edit?gid=0#gid=0 |
| Detailed Info — review.csv | https://docs.google.com/spreadsheets/d/13U9ErL8zc9NpFk7izuoa72j33GUf4D3xDHSeZYaSuCM/edit?gid=1771484280#gid=1771484280 |
| Review CSV Generator Tool | https://script.google.com/a/macros/turing.com/s/AKfycbzi9BTJ8iVwPCCEGGaiaII9bKUwVl62mxkRpwGDfRYIKphxiDBfO-oF4B3A8Bc9AgYU/exec |
| QC Tool V2 | https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer |
| QC Tool V1 | https://qc-api-713053229214.us-central1.run.app/ |
| Harbour QC Parking Lot V2 | https://script.google.com/a/macros/turing.com/s/AKfycbynPi3chsymglRXlDIlZgrreMLocnN35fHJ90-MC424cuAhkW-p2KMrzvcOLGCkNJJ4uA/exec |
| Harbour QC Parking Lot V1 | https://script.google.com/a/macros/turing.com/s/AKfycbzpJpE_d-lZrg8k7p_mDHEvpLiqKHi_TCBnbAfPf7aKvr0ZPRNfDspVL15elVc-xGab/exec |

## 3 Golden Tasks (accepted by client)

### 1. atlanta-itinerary-settlement-standing-ranked (Slack connector)

**Instruction:** User closing room list for Phoenix summit. Posted reminder about what finance accepts as covered travel. Six people replied. Judge each person's arrangement against four things the reminder names. Two traps: certainty ≠ eligibility; fine for getting there ≠ must be on list.

**Deliverable:** Reply in thread with SUMMIT ROOM LIST, one line per person (COVERED or NOT COVERED), then short reasons.

**Shape:** Eligibility judgement with contested rows — binary verdicts, hedging impossible, contested on real bridge.

### 2. how-much-of-my-drive-is-link-only (Google Drive connector)

**Instruction:** Going on leave, need honest split of drive. Real material only (documents, spreadsheets, decks, drawings, PDFs — no video/notes/config/folders/shortcuts/binned). How much open at all, how much link-only (can't walk to it). How many separate people leaning on, how much shared to me alone.

**Deliverable:** answers.json with material_i_can_open, link_only, people_i_depend_on, shared_to_me_alone.

**Shape:** Multi-hop counting along containment axis — shared enumerated base, fields nest, hold definitions apart.

### 3. outside-voices-in-the-locked-sales-drive (Google Drive connector)

**Instruction:** Reconciliation — who posted in threads vs who is on sharing list. Then reach and exposure across the rest of drive.

**Deliverable:** Report + JSON of rosters.

**Shape:** Reconciliation across two populations — one by behaviour (posted), one by grant (on list). Requires both rosters + difference + relations (reach, expiry, ownership).

## Key patterns from golden tasks (from doc 07)

- **Difficulty from work, never from ambiguity** — every fork pinned or promoted
- **One new relation over already-correct roster** — chained, sharp, oracle-proven
- **Structure disclosed in prompt, then graded** — prevents stub passing
- **Connector surface closed in environment** — fail closed at every layer
- **Evidence with frozen folder, one checksum** — infra excluded, numbers re-derived
- **review.csv as history** — append, never overwrite
