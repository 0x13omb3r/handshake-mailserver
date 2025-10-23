#! /usr/bin/python3
# (c) Copyright 2019-2025, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import argparse
import json
import smtplib

from policy import this_policy as policy


def post(smtp_rcpt, template, data, server="127.0.0.1"):
    # CODE - merge data into template
    msg = ""
    with smtplib.SMTP("127.0.0.1", 25) as smtp_cnx:
        smtp_from = policy.get("manager_account") + "@" +policy.get("email_domains")
        smtp_cnx.sendmail(smtp_from, smtp_rcpt, msg.as_string())
        smtp_cnx.quit()

def main():
    parser = argparse.ArgumentParser(description='EPP Jobs Runner')
    parser.add_argument("-s", '--server', default="127.0.0.1")
    parser.add_argument("-r", '--recipients', required=True)
    parser.add_argument("-m", '--message', required=True)
    args = parser.parse_args()
    post(args.recipients.split(","),args.message,json.loads(args.data),args.srver)


if __name__ == "__main__":
    main()
