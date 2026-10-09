Our first-quarter access review is due and I want it done on my Google Drive. I am the Drive owner; use the gws tools.

Apply our data-classification and access policy, /workspace/provided/access_classification_policy.docx, to every
Google Sheets spreadsheet in my Drive that is not in the trash and is shared with anyone other than me. The policy relies on the
collaborator roster, /workspace/provided/collaborator_roster.csv, and on the register of approved exceptions,
/workspace/provided/access_exceptions.xlsx.

Wherever a spreadsheet's sharing gives someone more than the policy allows, fix it in Drive: reduce that grant to the highest role the
policy allows, or remove it when the policy allows no access at all. Leave every grant the policy allows exactly as it is, keep my own
ownership, add no sharing, do not change sharing on any other file, and do not edit any spreadsheet's content.

Work through this systematically:
1. Start by listing all your spreadsheets with `gws drive files list`. The response includes permissions inline — identify the shared ones (any file with a non-owner grant).
2. For each shared spreadsheet, read its full grid data with `gws sheets spreadsheets get` — include all tabs, not just the first. Classify it by matching its cell labels against the policy tiers.
3. For each grant that exceeds the policy, fix it with `gws drive permissions update` (to reduce to reader/commenter) or `gws drive permissions delete` (to remove entirely).
4. Do not re-read or re-process any spreadsheet you have already classified. Work through the list once, in order.
5. Read the policy document, roster, and exceptions register once at the start, then apply them to every grant. Do not re-read these files for each spreadsheet.

Then write the review up in two files.

1. /workspace/access_review.xlsx with three sheets:
     Classification  header Spreadsheet ID, Classification; then one row per spreadsheet you reviewed, by Drive file id, with its
                     tier as the policy names it (Restricted, Confidential or Internal)
     Changes         header Permission ID, Spreadsheet ID, Action; then one row per grant you changed: the permission id as Drive
                     reports it, the spreadsheet's file id, and the Action "Removed" or "Reduced to " followed by the new role
                     as Drive names it (reader, commenter or writer)
     Summary         header Measure, Value; then exactly five rows, numbers not formulas: Spreadsheets reviewed, Restricted,
                     Confidential, Grants removed, Grants reduced
   Put nothing else on any sheet.

2. /workspace/restricted_access_memo.docx, a one-page memo to our Privacy Officer, containing a table with the header row
   Spreadsheet ID | People with access after review, and one row per Restricted spreadsheet giving, as a plain number, how many
   people other than me can still open it once your changes are made (0 when nobody can).
