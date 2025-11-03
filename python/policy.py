#! /usr/bin/python3
# (c) Copyright 2019-2025, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import json
import sys

import fileloader

DEFAULT_POLICY_VALUES = {
    "email_domain": "webmail.localhost",
    "website_domain": "example.com",
    "website_title": "Handshake Webmail",
    "logging_default": "local0",
    "strict_referrer": True,
    "allow_icann_domains": False,
    "session_expiry": 60 * 60 * 2,
    "never_active_account_expire": 7,
    "was_active_account_expire": 30,
    "manager_account": "manager",
    "icann_smtp_relay": None,
    "cert_site_fqdn": "handshake.webmail",
    "cert_site_country": "GB",
    "cert_site_location": "London",
    "cert_site_org": "Handshake",
    "cert_site_org_unit": "Ops",
    "cert_site_state": "London"
}


class Policy:
    """ policy values manager """

    def __init__(self):
        self.BASE = os.environ.get("BASE", "/opt/data")
        self.SERVICE = os.path.join(self.BASE, "service")

        self.POLICY_FILE = os.path.join(self.SERVICE, "config", "policy.json")
        self.DOMAINS_FILE = os.path.join(self.SERVICE, "config",
                                         "used_domains.json")
        self.USER_DIR = os.path.join(self.SERVICE, "users")
        self.HOME_DIR = os.path.join(self.SERVICE, "homedirs")
        self.MBOX_DIR = os.path.join(self.SERVICE, "mailboxes")
        self.EMAILS_DIR = os.path.join(self.SERVICE, "emails")
        self.SESSIONS_DIR = os.path.join(self.SERVICE, "sessions")
        self.RESET_CODES = os.path.join(self.SERVICE, "reset_codes")
        self.BASE_UX_DIR = "/usr/local/etc/uid"

        if not os.path.isfile(self.POLICY_FILE):
            with open(self.POLICY_FILE, "w+") as fd:
                json.dump(DEFAULT_POLICY_VALUES, fd, indent=2)

        self.file = fileloader.FileLoader(self.POLICY_FILE)
        self.all_data = None
        self.merge_policy_data()

        with open("/usr/local/etc/build.txt", "r") as fd:
            self.all_data["build"] = fd.readline().strip()

    def merge_policy_data(self):
        self.all_data = DEFAULT_POLICY_VALUES.copy()
        self.all_data.update(self.file.data())

    def check_file(self):
        if self.file.check_for_new():
            self.merge_policy_data()

    def get(self, name, default_value=None):
        self.check_file()
        return self.all_data.get(name, default_value)

    def data(self):
        self.check_file()
        return self.all_data


this_policy = Policy()

if __name__ == "__main__":
    print(this_policy.get(sys.argv[1]))
