#! /usr/bin/python3
# (c) Copyright 2019-2025, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import argparse
import jinja2
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import uconfig
from policy import this_policy as policy
from log import this_log as log

DO_NOT_INCLUDE_TAGS = {"X-Env-From", "BCC"}
MULTILINE_TAGS = {"To", "CC", "BCC"}


def post(template, data, server="127.0.0.1"):
    src = os.path.join(policy.EMAILS_DIR, template + ".eml")
    if not os.path.isfile(src):
        return False, f"Template file {template} not found"

    smtp_from = policy.get("manager_account") + "@" + policy.get(
        "email_domain")

    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(policy.EMAILS_DIR))
    template = environment.get_template(template + ".eml")
    data["policy"] = policy.data()
    content = template.render(**data)
    header = {}
    lines = [line.rstrip() for line in content.split("\n")]
    msg = MIMEMultipart('alternative')

    while (len(lines) and len(lines[0]) and (colon := lines[0].find(":")) > 0
           and (space := lines[0].find(" ")) > 0 and space > colon):

        tag = lines[0][:colon].strip()
        rest = lines[0][colon + 1:].strip()

        if tag in header and len(header[tag]) > 0 and tag in MULTILINE_TAGS:
            header[tag] += "," + rest
        else:
            header[tag] = rest

        del lines[0]

    if "To" not in header and "user" in data and "user" in data["user"]:
        header["To"] = data["user"]["user"] + "@" + policy.get("email_domain")

    if "From" not in header:
        header["From"] = smtp_from

    if "From" not in header or "To" not in header or "Subject" not in header:
        return False, "Header missing critical lines"

    msg.attach(MIMEText("\n".join(lines), 'html'))

    log.debug(f"Sending email {template} to {header['To']}")

    print(">>>>>", json.dumps(header, indent=2))
    print(">>>>>", json.dumps(lines, indent=2))
    return False, None

    smtp_rcpt = []
    for hdr_tag in MULTILINE_TAGS:
        if hdr_tag in header and len(header[hdr_tag]) > 0:
            for each in header[hdr_tag].split(","):
                smtp_rcpt.append(each)

    with smtplib.SMTP("127.0.0.1", 25) as smtp_cnx:
        smtp_cnx.sendmail(smtp_from, smtp_rcpt, msg.as_string())
        smtp_cnx.quit()

    return True, None


def main():
    parser = argparse.ArgumentParser(description='EPP Jobs Runner')
    parser.add_argument("-s", '--server', default="127.0.0.1")
    parser.add_argument("-m", '--message', required=True)
    parser.add_argument("-d", '--data', required=True)
    parser.add_argument("-u", '--user')
    args = parser.parse_args()
    data = json.loads(args.data)
    if args.user:
        ok, this_user = uconfig.user_info_load(args.user)
        if ok:
            data["user"] = this_user
        else:
            print(f"ERROR: {args.user} - {this_user}")
    post(args.message, data, args.server)


if __name__ == "__main__":
    main()
