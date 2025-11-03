#! /usr/bin/python3

import argparse
import base64

import misc
import uconfig
import validation
from policy import this_policy as policy


def is_allowed_email(in_user, in_email):
    if not validation.is_valid_account(
            in_user) or not validation.is_valid_email(in_email):
        return False, "Failed: basic valiadation"

    user = in_user.rstrip('.').lower()
    frm, dom = in_email.split("@")
    email = f"{frm}@{dom.rstrip('.').lower()}"

    ok, user_data = uconfig.load(user, with_events=False)
    if not ok:
        return False, "Failed: load user"

    if not misc.is_user_active(user_data):
        return False, "Failed: misc.is_user_active"

    email_domain = policy.get("email_domain").rstrip(".").lower()
    if dom == email_domain and frm == user:
        return True, "default address"

    if "identities" not in user_data or email not in user_data["identities"]:
        return False, "Not an active identity"

    if not misc.is_email_active(user_data, email):
        return False, "Failed: misc.is_email_active"

    return True, None


def main():
    parser = argparse.ArgumentParser(
        description='Check a user is allowed to use an email address')
    parser.add_argument("-e", '--email', required=True)
    parser.add_argument("-u", '--user', required=True)
    parser.add_argument("-D", '--debug', action="store_true")
    args = parser.parse_args()

    email = base64.b64decode(args.email).decode("utf-8")
    user = base64.b64decode(args.user).decode("utf-8")

    ok, reply = is_allowed_email(user, email)
    if args.debug:
        print("Final answer:", user, email, "=", ok, "-", reply)

    if ok:
        print("OK", end="")
    else:
        print("BAD", end="")


if __name__ == "__main__":
    main()
