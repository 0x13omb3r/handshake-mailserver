#! /usr/bin/python3
# (c) Copyright 2019-2025, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import tempfile
import time
import os
import json
import passlib.hash
import secrets
import base64
import validators

from policy import this_policy as policy
import executor
import validation
import uconfig
import misc
from log import this_log as log


def encrypt(password, salt=None):
    return passlib.hash.sha512_crypt.hash(password, rounds=5000, salt=salt)


def compare_passwords(plaintext, stored):
    parts = stored.split("$")
    return encrypt(plaintext, parts[2]) == stored


def create_session_file(user, user_data, user_agent):
    with tempfile.NamedTemporaryFile(
            "w+",
            dir=policy.SESSIONS_DIR,
            encoding="utf-8",
            delete=False,
            prefix=misc.make_session_code(user)) as fd:
        json.dump({"user": user, "agent": user_agent}, fd)
        session_code = os.path.basename(fd.name)

    user_data["session"] = session_code
    user_data["user"] = user

    return True, user_data


def login(sent_data, user_agent):
    if sent_data.get("user", None) is None or sent_data.get("password",
                                                            None) is None:
        return False, "Insufficient data"

    ok, user_data = uconfig.user_info_load(sent_data["user"])
    if not ok or user_data is None or "password" not in user_data:
        return False, f"User '{sent_data['user']}' not found or missing password"

    if not compare_passwords(sent_data["password"], user_data["password"]):
        return False, "Password does no match"

    uconfig.user_info_update(sent_data["user"], {"last_login_dt": misc.now()})
    return create_session_file(sent_data["user"], user_data, user_agent)


def check_session(session_code, user_agent):
    file = os.path.join(policy.SESSIONS_DIR, session_code)
    now = time.time()

    if not os.path.isfile(file):
        return False, f"Session file '{file}' missing"

    session_expire_time = policy.get("session_expiry")
    if os.path.getmtime(file) + session_expire_time <= now:
        os.remove(file)
        return False, "Session file too old"

    with open(file, "r") as fd:
        js = json.load(fd)

    if "agent" not in js or js["agent"] != user_agent or "user" not in js:
        os.remove(file)
        return False, "Session file missing data or user-agent mismatch"

    ok, user_data = uconfig.user_info_load(js["user"])
    if not ok or user_data is None:
        return False, "User in session file doesn't exist"

    os.utime(file, (now, now))
    user_data["session"] = session_code

    return True, user_data


def check_password(user, sent_data):
    ok, user_data = uconfig.user_info_load(user)
    return compare_passwords(sent_data["password"], user_data["password"])


def logout(session_code, user, user_agent):
    ok, user_data = check_session(session_code, user_agent)
    if not ok or user_data is None:
        return False, "Session code failed to checkout"

    os.remove(os.path.join(policy.SESSIONS_DIR, session_code))
    return True, None


def valid_reset_pin(pin):
    if not isinstance(pin, str) or len(pin) != 4 or not pin.isdecimal():
        return False, "Invalid PIN"
    return True, None


PASSWORD_REQUEST_WEB = {
    "email": [True, validators.email],
    "pin": [True, valid_reset_pin]
}


def request_password_reset(user, sent_data):
    log.log(f"{user}: {sent_data}")
    ok, reply = validation.web_validate(sent_data, PASSWORD_REQUEST_WEB)
    if not ok:
        return False, reply

    executor.create_command(
        "webui_password_request", "doms", {
            "verb": "request_password_reset",
            "data": {
                "email": sent_data["email"],
                "pin": sent_data["pin"]
            }
        })

    return True, None


REGISTER_WEB = {
    "user": [True, validation.web_valid_new_account],
    "email": [True, validators.email],
    "password": [True, None],
    "confirm": [True, None]
}


def register(sent_data, user_agent):
    ok, reply = validation.web_validate(sent_data, REGISTER_WEB)
    if not ok:
        return False, reply

    if sent_data["password"] != sent_data["confirm"]:
        return False, "Passwords do not match"

    user = sent_data["user"]
    now = misc.now()
    user_data = {
        "mx":
        base64.b32encode(secrets.token_bytes(30)).decode("utf-8").lower(),
        "password": encrypt(sent_data["password"]),
        "created_dt": now,
        "amended_dt": now,
        "last_login_dt": now,
        "email": sent_data["email"],
        "events": [{
            "when_dt": now,
            "desc": "Account first registered"
        }],
        "identities": [],
        "domains": {
            user: False
        }
    }

    file = uconfig.user_file_name(user, True)
    with open(file, "w+") as fd:
        json.dump(user_data, fd, indent=2)

    executor.create_command("new_user_added", "doms", {
        "verb": "new_user_added",
        "data": {
            "user": user
        }
    })
    return create_session_file(user, user_data, user_agent)


def close_account(user):
    file = uconfig.user_file_name(user)
    log.debug(f"close_account: {user} - {file}")
    if not os.path.isfile(file):
        return False, "User not found"

    os.remove(file)
    executor.create_command("webui_account_closed", "doms", {
        "verb": "account_closed",
        "data": {
            "user": user
        }
    })
    return True, None


def password_new(user, password):
    uconfig.user_info_update(user, {"password": encrypt(password)})
    executor.create_command("webui_password_changed", "doms",
                            {"verb": "password_changed"})
    return True


def valid_reset_code(code):
    if len(code) != 43:
        return False, "Invalid reset code"
    return True, None


PASSWORD_RESET_WEB = {
    "code": [True, valid_reset_code],
    "pin": [True, valid_reset_pin],
    "password": [True, None]
}


def reset_user_password(sent_data):
    ok, reply = validation.web_validate(sent_data, PASSWORD_RESET_WEB)
    if not ok:
        return False, reply

    store_code = misc.make_hash(sent_data["code"] + ":" + sent_data["pin"])
    file = os.path.join(policy.RESET_CODES, store_code)
    if not os.path.isfile(file):
        return False, "Invalid reset code"
    try:
        with open(file, "r") as fd:
            this_user = json.load(fd)
    except Exception:
        os.remove(file)
        return False, "Invalid reset code"
    os.remove(file)

    if (user := this_user.get("user", None)) is None:
        return False, "Invalid reset code"

    ok, user_data = uconfig.user_info_load(user)
    if not ok:
        return False, "Invalid reset code"

    uconfig.user_info_update(user,
                             {"password": encrypt(sent_data["password"])})

    return True, None


if __name__ == "__main__":
    print("INFO LOAD ->", uconfig.user_info_load("lord.webmail"))


def debug_stuff():
    print(
        "REGISTER >>>",
        register(
            {
                "user": "anon.webmail",
                "email": "earl@gmail.com",
                "password": "yes",
                "confirm": "yes"
            }, "my-agent"))
    # print(uconfig.user_info_load("james"))
    # print(uconfig.user_info_update("james", {"user": "james", "password": "fred"}))
    # print(uconfig.user_info_load("james"))
    # print(uconfig.user_info_update("james", None))
    # print(uconfig.user_info_load("james"))
    # print(password_compare("yes","lord.webmail"))
    # print(check_session("abc123","fred"))

    ok, uid = login({"user": "lord.webmail", "password": "yes"}, "my-agent")
    print("LOGIN ->", ok, uid)
    if ok:
        print("CHECK_SESSION ->", check_session(uid["session"], "my-agent"))

    print("")
    print("INFO LOAD ->", uconfig.user_info_load("lord.webmail"))
    print("INFO ADD ->",
          uconfig.user_info_update("lord.webmail", {"temp": "value"}))
    print("INFO LOAD ->", uconfig.user_info_load("lord.webmail"))
    print("INFO ADD ->",
          uconfig.user_info_update("lord.webmail", {"temp": None}))
    print("INFO LOAD ->", uconfig.user_info_load("lord.webmail"))
    # print(misc.make_session_code("james"))
