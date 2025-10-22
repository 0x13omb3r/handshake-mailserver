#! /usr/bin/python3
# (c) Copyright 2019-2025, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import smtplib

from policy import this_policy as policy


def post(all_rcpt, template, data):
    # CODE - merge data into template
    msg = ""
    with smtplib.SMTP("127.0.0.1", 25) as smtp_cnx:
        smtp_cnx.sendmail(
            policy.get("manager_account") + "@" +
            policy.get("default_mail_domain"), all_rcpt, msg.as_string())
        smtp_cnx.quit()
