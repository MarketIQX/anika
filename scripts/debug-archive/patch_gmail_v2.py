from pathlib import Path
p = Path("app/tools/gmail_tool.py")
code = p.read_text(encoding="utf-8")

OLD = '''    s = get_settings()
    return (
        f'from:{s.prakasha_email} '
        f'subject:"Balakrishna and Co" '
        f'-subject:"Payment" '
        f'-subject:"outstanding" '
        f'-subject:"Invoice" '
        f'is:unread '
        f'-label:{PROCESSED_LABEL} '
        f'newer_than:7d'
    )'''

NEW = '''    s = get_settings()
    # Two-clause query joined with OR:
    #   A) Website-form notifications (self-sent with fixed subject)
    #   B) Direct new enquiries TO prakasha@balakrishnaandco.com:
    #        - NOT a reply (Gmail operator: -"Re:" -"Fwd:" in subject)
    #        - NOT from known automation domains
    #        - NOT in promotions/updates/social/forums Gmail categories
    return (
        "("
        f'(from:{s.prakasha_email} subject:"Balakrishna and Co" '
        f'-subject:"Payment" -subject:"outstanding" -subject:"Invoice")'
        " OR "
        f'(to:{s.prakasha_email} '
        f'-from:{s.prakasha_email} '
        f'-subject:"Re:" -subject:"Fwd:" -subject:"FW:" '
        f'-subject:"Payment" -subject:"outstanding" -subject:"Invoice" '
        f'-subject:"Statement" -subject:"Intimation" -subject:"Refund" '
        f'-subject:"OTP" -subject:"Receipt" -subject:"Account" '
        f'-from:*@icicibank.com -from:*@zerodha.com '
        f'-from:*@taxmann.com -from:*@nse.co.in -from:*@bse.co.in '
        f'-from:*@google.com -from:*@googleworkspace.com '
        f'-from:*@incometax.gov.in -from:*@cpc.incometax.gov.in '
        f'-from:no-reply@* -from:noreply@* -from:donotreply@* '
        f'-from:*@dhruvaadvisors.com -from:*@investing.com '
        f'-category:promotions -category:updates '
        f'-category:social -category:forums)'
        ") "
        f'is:unread '
        f'-label:{PROCESSED_LABEL} '
        f'newer_than:7d'
    )'''

if OLD not in code:
    print("PATTERN NOT FOUND")
else:
    p.write_text(code.replace(OLD, NEW), encoding="utf-8")
    print("Gmail query now catches: website forms + direct fresh enquiries only.")
