import smtplib
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from difflib import HtmlDiff
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from sender_policy_flattener.formatting import format_records_for_email

_email_style = """
    <style type="text/css">
        body {font-family: "Helvetica Neue Light", "Lucida Grande", "Calibri", "Arial", sans-serif;}
        a {text-decoration: none; color: royalblue; padding: 5px;}
        a:visited {color: royalblue}
        a:hover {background-color: royalblue; color: white;}
        h1 {
            font-family: "Helvetica Neue Light", "Lucida Grande", "Calibri", "Arial", sans-serif;
            font-size: 14pt;
        }
        table.diff {border: 1px solid black;}
        td {padding: 5px;}
        td.diff_header {text-align:right}
        .diff_header {background-color:#e0e0e0}
        .diff_next {background-color:#c0c0c0}
        .diff_add {background-color:#aaffaa}
        .diff_chg {background-color:#ffff77}
        .diff_sub {background-color:#ffaaaa}
    </style>
    """



def email_changes(
    zone, prev_addrs, curr_addrs, subject, server, fromaddr, toaddr, api_key='', test=False
):
    bindformat = format_records_for_email(curr_addrs)
    prev_addrs = " ".join(prev_addrs)
    curr_addrs = " ".join(curr_addrs)
    prev = sorted([s for s in prev_addrs.split() if "ip" in s])
    curr = sorted([s for s in curr_addrs.split() if "ip" in s])

    print("Do we have a API Key?")
    print(api_key)

    diff = HtmlDiff()
    table = diff.make_table(
        fromlines=prev, tolines=curr, fromdesc="Old records", todesc="New records"
    )

    header = "<h1>Diff</h1>"
    html = _email_style + bindformat + header + table
    

    message = Mail(
        from_email=fromaddr,
        to_emails=toaddr,
        subject=subject,
        html_content=html)
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)


