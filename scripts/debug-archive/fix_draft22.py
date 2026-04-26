from app.db import execute

correct_body = '''Dear Ms. Chandrika,

Thank you for reaching out and sharing your background in detail.

We confirm that your requirement falls well within our area of practice. Based on your situation—transitioning from NRI status, returning to India briefly, and then relocating to Germany—your case will involve careful evaluation of residential status under Indian tax laws, determination of taxability of income during your stay in India, and applicability of the Double Taxation Avoidance Agreement (DTAA) between India and Germany.

Broadly, the following aspects will need to be analysed:
- Residential status in India for FY 2024-25 based on your period of stay
- Taxability of income earned while working in India during your short stay
- Implications once you relocate to Germany and become a tax resident there
- DTAA provisions to avoid double taxation on cross-border income
- Requirement and applicability of filing Income Tax Return (ITR) in India

For a detailed and accurate advisory, we would require the following information:
- Travel history (number of days stayed in India for FY 2024-25 and preceding 4 years)
- Details of employment in India (salary structure, duration, employer details)
- Expected date of relocation to Germany
- Whether any income will continue to accrue or arise in India after relocation
- Copy of passport (or travel summary) for residential status determination

Our professional fee for a detailed consultation and advisory note on your tax position would be Rs. 7,500/- plus GST.

If you would like to proceed, we can schedule a consultation call at your convenience. Please feel free to suggest a suitable time.

Looking forward to assisting you.

Yours faithfully,
CA Prakasha
Partner, Balakrishna & Co. | BKPS & Co LLP
Chartered Accountants
Phone: 8618259712
Email: prakasha@balakrishnaandco.com'''

# Turn off the auto-signature flag so it doesn't append anything
execute('UPDATE drafts SET body=?, uses_signature=0 WHERE id=22', (correct_body,))
print('Draft 22 body replaced. No auto-signature.')
