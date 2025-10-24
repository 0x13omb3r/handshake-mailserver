#! /usr/bin/python3
# (c) Copyright 2019-2025, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import datetime
import idna
import hashlib
import secrets
import base64
import time
import os


def now(offset=0):
    time_now = datetime.datetime.now()
    time_now += datetime.timedelta(seconds=offset)
    return time_now.strftime("%Y-%m-%d %H:%M:%S")


def puny_to_utf8(name):
    try:
        idn = idna.decode(name)
        return idn
    except idna.IDNAError:
        try:
            idn = name.encode("utf-8").decode("idna")
            return idn
        except UnicodeError:
            return None
    return None


def utf8_to_puny(utf8):
    try:
        puny = idna.encode(utf8)
        return puny.decode("utf-8")
    except idna.IDNAError:
        try:
            puny = utf8.encode("idna")
            return puny.decode("utf-8")
        except UnicodeError:
            return None
    return None


def debug_mode():
    return os.environ.get("DEBUG_MODE", "N") == "Y"


def as_simple_text(data):
    return base64.b64encode(data).decode("utf-8").translate(
        str.maketrans({
            "/": "-",
            "=": "",
            "+": "_"
        }))


def do_make_hash(src):
    hsh = hashlib.sha256()
    for x in range(0, 10):
        hsh.update(src.encode("utf-8"))
    return as_simple_text(hsh.digest())


def make_hash(src):
    for x in range(0, 1000):
        src = do_make_hash(src)
    return src


def make_session_code(user):
    """ make a user's session code - sent to the user """
    hsh = hashlib.sha256()
    hsh.update(secrets.token_bytes(500))
    hsh.update(str(user).encode("utf-8"))
    hsh.update(str(os.getpid()).encode("utf-8"))
    hsh.update(str(time.time()).encode("utf-8"))
    return as_simple_text(hsh.digest())


if __name__ == "__main__":
    x = make_session_code("james")
    print(x)
    print(make_hash(x + ":" + "1234"))
    print(make_hash(x + ":" + "1234"))


def not_this_time():
    for x in ["xn--belgi-rsa.be", "xn--9q8h.ss-test-1", "fred.com"]:
        utf8 = puny_to_utf8(x)
        print(x, "->", utf8)
        puny = utf8_to_puny(utf8)
        print(utf8, "->", puny)
