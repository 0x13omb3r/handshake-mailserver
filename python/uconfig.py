#! /usr/bin/python3
# (c) Copyright 2019-2025, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import filelock
import json

import misc
from policy import this_policy as policy


def calc_hash(user):
    if user == policy.get("manager_account"):
        return ["00", "00"]

    hashval = 2166136261
    for ch in user:
        hashval = hashval * 16777619
        hashval = hashval ^ ord(ch)
    ret = hex(hashval & 0xffff).upper()[2:]
    return [ret[:2], ret[2:]]


def user_file_name(user, with_make_dir=False, with_lock_name=False):
    this_hash = calc_hash(user)
    if with_make_dir:
        d = policy.USER_DIR
        for dir in [this_hash[0], this_hash[1]]:
            d = os.path.join(d, dir)
            if not os.path.isdir(d):
                os.mkdir(d, mode=0o755)
    path = os.path.join(policy.USER_DIR, this_hash[0], this_hash[1])
    if with_lock_name:
        return os.path.join(path, user + ".json"), os.path.join(path, ".lock")
    else:
        return os.path.join(path, user + ".json")


def return_user(js, user):
    if user not in js:
        return None
    ret_user = js[user]
    ret_user["user"] = user
    return ret_user


def load(user, with_events=True):
    user_file = user_file_name(user)
    if not os.path.isfile(user_file):
        return None, "File not found"

    with open(user_file, "r") as fd:
        js = json.load(fd)

    js["user"] = user
    if not with_events and "events" in js:
        del js["events"]
    return True, js


def update(user, data, with_events=True):
    user_file, lock_file = user_file_name(user, with_lock_name=True)
    if not os.path.isfile(user_file):
        return None

    if data is None and os.path.isfile(user_file):
        os.remove(user_file)
        return True, None

    with filelock.FileLock(lock_file):

        with open(user_file, "r") as fd:
            js = json.load(fd)

            for item in data:
                this_data = data[item]
                if this_data is None:
                    if item in js:
                        del js[item]
                else:
                    if item == "events":
                        if isinstance(this_data, dict):
                            if "when_dt" not in this_data:
                                this_data["when_dt"] = misc.now()
                            js[item].append(this_data)
                        elif isinstance(this_data, list):
                            for each_event in this_data:
                                if "when_dt" not in each_event:
                                    each_event["when_dt"] = misc.now()
                                js[item].append(each_event)
                    else:
                        js[item] = this_data

        js["amended_dt"] = misc.now()
        new_file = user_file + ".new"
        with open(new_file, "w") as fd:
            json.dump(js, fd, indent=2)
        os.replace(new_file, user_file)

        js["user"] = user
        if not with_events and "events" in js:
            del js["events"]

        return True, js


if __name__ == "__main__":
    print("INFO LOAD ->", load("anon.webmail"))
    print("INFO UPDATE ->",
          update("anon.webmail", {"events": {
              "desc": "Some event"
          }}))
    print("INFO LOAD ->", load("anon.webmail"))
    # print("INFO ADD ->",
    #       update("anon.webmail", {"temp": "value"}))
    # print("INFO LOAD ->", load("anon.webmail"))
    # print("INFO ADD ->",
    #       update("anon.webmail", {"temp": None}))
    # print("INFO LOAD ->", load("anon.webmail"))
    # print("INFO LOAD ->", load("anon.webmail"))
