#! /usr/bin/python3

import os
import json
import time
import subprocess
import argparse
import base64

from policy import this_policy as policy
import executor
import uconfig
import resolv
import sendmail
import validation
import icann_tlds
from log import this_log as log
import misc

RR_MX = 15


def is_user_active(user_data):
    if (user := user_data.get("user", None)) is None:
        return False
    if (doms := user_data.get(
            "domains",
            None)) is None or not isinstance(doms, dict) or user not in doms:
        return False
    return doms[user]


def is_email_active(user_data, email):
    if (doms := user_data.get("domains", None)) is None:
        return False
    split_mail = email.rstrip(".").lower().split("@")
    return split_mail[1] in doms and doms[split_mail[1]]


def check_mx_match(user_mx, mx_rrs):
    if ((user_mx is None) or (mx_rrs is None)
            or (mx_rrs.get("Status", 99) != 0) or ("Answer" not in mx_rrs)
            or (not isinstance(mx_rrs["Answer"], list))
            or (len(mx_rrs["Answer"]) != 1)):
        return False

    mx = mx_rrs["Answer"][0]
    if mx.get("type", 0) != RR_MX or mx.get("data", None) is None:
        return False

    mx_rr = mx["data"].split()[1].rstrip(".").lower()
    chk_rr = (user_mx + "." + policy.get("email_domain")).rstrip(".").lower()

    return chk_rr == mx_rr


def user_to_json(user_data):
    return json.dumps({
        "domains": user_data["domains"],
        "identities": user_data["identities"]
    })


def user_has_changed(old_user, this_user):
    return user_to_json(old_user) != user_to_json(this_user)


def clean_up_emails(emails):
    email_domain = policy.get("email_domain").rstrip(".").lower()
    new_list = []
    for email in [e for e in emails if validation.is_valid_email(e)]:
        user, dom = email.split("@")
        if dom != email_domain:
            new_list.append([user, dom.rstrip(".").lower()])
    return new_list


def active_uid(this_user):
    return this_user.get("uid", 0) > 100


class UserData:

    def __init__(self):
        self.users_just_activated = {}
        self.need_remake_mail_files = False
        self.need_remake_unix_files = False
        self.resolver = None
        self.active_users = {}

    def startup(self):
        self.resolver = resolv.Resolver()
        self.load_user_details()

    def load_user_details(self):
        self.load_users()
        self.active_users = {
            user: True
            for user in self.all_users if is_user_active(self.all_users[user])
        }

        for user in self.active_users:
            this_user = self.all_users[user]
            if not active_uid(this_user):
                self.assign_uid(this_user)

    def finish_start_uo(self):
        self.run_mx_check(None)
        self.check_remake_files()

    def assign_uid(self, this_user):
        if active_uid(this_user):
            return
        user = this_user["user"]
        this_uid = self.find_free_uid()
        self.active_users[user] = True
        this_user["uid"] = this_uid
        uconfig.update(user, {"uid": this_uid}, with_events=False)
        executor.create_command("doms_runner_user_add", "root", {
            "verb": "make_home_dir",
            "data": {
                "uid": this_uid,
                "user": user
            }
        })
        self.need_remake_unix_files = True

    def load_users(self):
        all_user_files = subprocess.run([
            "/bin/busybox", "find", policy.USER_DIR, "-type", "f", "-name",
            "*.json"
        ],
                                        capture_output=True)
        self.all_users = {}
        manager_account = policy.get("manager_account")
        for file in all_user_files.stdout.decode('utf-8').strip().split():
            user = file.split("/")[-1][:-5]
            if user != manager_account:
                ok, reply = uconfig.load(user, with_events=False)
                if ok:
                    self.all_users[user] = reply

    def remake_unix_files(self, data):
        base_data = {}
        manager_account = policy.get("manager_account")
        ok, manager_info = uconfig.load(manager_account, with_events=False)

        for file in ["passwd", "shadow", "group"]:
            with open(os.path.join(policy.BASE_UX_DIR, file), "r") as fd:
                base_data[file] = [line.strip() for line in fd.readlines()]

        with open("/run/passwd.tmp", "w+") as fd:
            lines = base_data["passwd"]
            if ok:
                lines.append(
                    f"{manager_account}:x:900:900::{os.path.join(policy.HOME_DIR, manager_account)}:/sbin/nologin"
                )
            for user in self.active_users:
                this_user = self.all_users[user]
                lines.append(
                    f"{user}:x:{this_user['uid']}:100::{os.path.join(policy.HOME_DIR, user)}:/sbin/nologin"
                )
            fd.write("\n".join(lines) + "\n")

        with open("/run/shadow.tmp", "w+") as fd:
            lines = base_data["shadow"]
            if ok:
                lines.append(
                    f"{manager_account}:{manager_info['password']}:20367:0:99999:7:::"
                )
            for user in self.active_users:
                this_user = self.all_users[user]
                lines.append(
                    f"{user}:{this_user['password']}:20367:0:99999:7:::")
            fd.write("\n".join(lines) + "\n")

        with open("/run/group.tmp", "w+") as fd:
            lines = [
                line for line in base_data["group"] if line[:6] != "users:"
            ]
            if ok:
                lines.append(f"{manager_account}:x:900:{manager_account}")
            lines.append("users:x:100:" + ",".join(list(self.active_users)))
            fd.write("\n".join(lines) + "\n")

        for file in ["passwd", "shadow", "group"]:
            os.replace(f"/run/{file}.tmp", f"/run/{file}.new")

        return True

    def find_free_uid(self):
        taken_uids = {
            self.all_users[user]["uid"]: True
            for user in self.active_users if active_uid(self.all_users[user])
        }
        for x in range(1000, 30000):
            if x not in taken_uids:
                return x
        return None

    def delete_user(self, user):
        if user in self.all_users:
            del self.all_users[user]
        if user in self.active_users:
            del self.active_users[user]

        file = uconfig.user_file_name(user)
        if os.path.isfile(file):
            os.remove(file)

        executor.create_command("doms_delete_user", "root", {
            "verb": "remove_home_dir",
            "data": {
                "user": user
            }
        })
        self.need_remake_mail_files = self.need_remake_unix_files = True

    def user_age_check(self, data):
        log.debug("User age check")

        for user in self.all_users:
            self.check_one_user(self.all_users[user], check_all_domains=True)

        never_active_old = misc.now(
            -86400 * policy.get("never_active_account_expire", 7))
        was_active_old = misc.now(-86400 *
                                  policy.get("was_active_account_expire", 30))

        for user in [u for u in self.all_users if u not in self.active_users]:
            this_user = self.all_users[user]
            if active_uid(this_user):
                if this_user["last_login_dt"] < was_active_old:
                    self.delete_user(user)
            else:
                if this_user["last_login_dt"] < never_active_old:
                    self.delete_user(user)

        return True

    def run_mx_check(self, data=None):
        self.users_just_activated = {}
        if data is not None:
            self.check_one_user(data)
        else:
            for user in self.all_users:
                self.check_one_user(self.all_users[user])
        return True

    def remake_mail_files_true(self, data):
        self.need_remake_mail_files = True
        return True

    def remake_unix_files_true(self, data):
        self.need_remake_unix_files = True
        return True

    def remake_mail_files(self, data):
        email_domain = policy.get("email_domain").rstrip(".").lower()
        icann_smtp_relay = policy.get("icann_smtp_relay", None)

        pfx = os.path.join(policy.BASE, "postfix", "data", "transport")
        with open(pfx + ".tmp", "w") as fd:
            fd.write(f"{email_domain} local: $myhostname\n")
            for user in self.active_users:
                doms = self.all_users[user]["domains"]
                for dom in [d for d in doms if doms[d]]:
                    fd.write(f"{dom} local: $myhostname\n")
            if icann_smtp_relay is not None:
                icann_smtp_relay = icann_smtp_relay.rstrip(".").lower()
                for tld in icann_tlds.ICANN_TLDS:
                    fd.write(f".{tld}:     smtp: [{icann_smtp_relay}]\n")

        pfx = os.path.join(policy.BASE, "postfix", "data", "virtual")
        with open(pfx + ".tmp", "w") as fd:
            fd.write(f"manager@{email_domain} manager\n")
            fd.write(f"root@{email_domain} manager\n")
            fd.write(f"postmaster@{email_domain} manager\n")
            fd.write(f"postfix@{email_domain} manager\n")
            for user in self.active_users:
                user_data = self.all_users[user]
                doms = user_data["domains"]
                for dom in [d for d in doms if doms[d]]:
                    fd.write(f"{dom}@{email_domain} {user}\n")
                for email in [
                        e for e in user_data["identities"]
                        if is_email_active(user_data, e)
                ]:
                    fd.write(f"{email} {user}\n")

        with open(policy.DOMAINS_FILE + ".tmp", "w") as fd:
            json.dump(
                {
                    dom: True
                    for user in Users.active_users
                    for dom in Users.all_users[user].get("domains", {})
                    if Users.all_users[user]["domains"][dom]
                }, fd)
        os.replace(policy.DOMAINS_FILE + ".tmp", policy.DOMAINS_FILE)

        for file in ["transport", "virtual"]:
            pfx = os.path.join(policy.BASE, "postfix", "data", file)
            os.replace(pfx + ".tmp", pfx + ".new")

        return True

    def check_remake_files(self):
        log.debug(
            f"need_remake_mail_files: {self.need_remake_mail_files}, need_remake_unix_files: {self.need_remake_unix_files}"
        )

        data = {"verb": "install_system_files"}

        if self.need_remake_mail_files:
            self.remake_mail_files(None)

        if self.need_remake_unix_files:
            self.remake_unix_files(None)
            if len(self.users_just_activated) > 0:
                data["data"] = {"with_doms_callback": "email_users_welcome"}

        if self.need_remake_mail_files or self.need_remake_unix_files:
            executor.create_command("doms_check_remake_files", "root", data)

        self.need_remake_unix_files = self.need_remake_mail_files = False

    def check_one_user(self, this_user, check_all_domains=False):
        user = this_user["user"]
        save_this_user = False
        this_user["events"] = []
        if (doms := this_user.get("domains", None)) is None:
            return

        for dom in [d for d in doms if not doms[d] or check_all_domains]:
            if self.check_one_domain(this_user, dom):
                save_this_user = True

        if save_this_user:
            log.debug(f"saving user '{user}'")
            ok, reply = uconfig.update(user, {
                "last_login_dt": misc.now(),
                "domains": this_user["domains"],
                "events": this_user["events"]
            },
                                       with_events=False)
            if ok:
                this_user = reply

    def check_one_domain(self, this_user, domain):
        user = this_user["user"]
        was_active = this_user["domains"].get(domain, False)
        dom_active = check_mx_match(this_user.get("mx", None),
                                    self.resolver.resolv(domain, "mx"))

        log.debug(
            f"check_one_domain {user}:{domain} = {dom_active} (was {was_active})"
        )

        if dom_active == was_active:
            return False  # domain status is unchanged

        self.need_remake_mail_files = True

        if user == domain:
            if was_active:
                del self.active_users[user]
            else:
                had_been_active = active_uid(this_user)
                if had_been_active:
                    log.debug(f"re-activated user {user}")
                    self.users_just_activated[user] = False
                else:
                    self.assign_uid(this_user)
                    log.debug(f"newly activated user {this_user}")
                    self.users_just_activated[user] = True
                self.active_users[user] = True
            self.need_remake_unix_files = True
        else:
            log.debug(f"newly activated domain {domain}")
            sendmail.post("new_domain", {"user": this_user, "domain": domain})

        this_user["domains"][domain] = dom_active
        this_user["events"].append({
            "desc":
            f"Domain '{domain}' is now {'active' if dom_active else 'inactive'}"
        })

        return True

    def email_users_welcome(self, data):
        for user, is_new in self.users_just_activated.items():
            email_type = "welcome" if is_new else "reactivated"
            sendmail.post(email_type, {"user": self.all_users[user]})

        self.users_just_activated = {}
        return True

    def identity_changed(self, data):
        emails = [
            item["Email"].rstrip(".") for item in json.loads(
                base64.b64decode(data.get("identities", "{}")).decode("utf-8"))
        ]
        if (user := base64.b64decode(data.get("user",
                                              None)).decode("utf-8")) is None:
            return False

        user = misc.utf8_to_puny(user.rstrip(".").lower())
        if user not in self.all_users:
            log.log(f"ERROR: user '{user}' does not seem to exist")
            return False

        emails = clean_up_emails(emails)

        log.debug(f"USER:{user} EMAILS:{emails}")

        this_user = self.all_users[user]
        old_user = this_user.copy()

        email_domain = policy.get("email_domain").rstrip(".").lower()

        this_user["identities"] = [user + "@" + dom for user, dom in emails]
        email_doms = [dom for __, dom in emails if dom != email_domain]

        for dom in list(this_user["domains"]):
            if dom not in email_doms and dom != user:
                del this_user["domains"][dom]

        for dom in email_doms:
            if dom not in this_user["domains"]:
                this_user["domains"][dom] = False

        this_user["identities"].sort()
        if not user_has_changed(old_user, this_user):
            log.debug("User hasn't changed")
            return True

        self.need_remake_mail_files = True

        ok, reply = uconfig.update(this_user["user"], {
            "events": {
                "desc": "Email Identities updated"
            },
            "identities": this_user["identities"],
            "domains": this_user["domains"]
        },
                                   with_events=False)
        if ok:
            this_user = reply

        self.run_mx_check(this_user)
        return True

    def new_user_added(self, data):
        if (user := data.get("user", None)) is None:
            return False
        ok, this_user = uconfig.load(user, with_events=False)
        if not ok or this_user is None:
            return False
        this_user["user"] = user
        self.all_users[user] = this_user
        return True

    def start_up_new_files(self, data):
        self.remake_unix_files(None)
        self.remake_mail_files(None)
        return True

    def dispatch_job(self, verb, data):
        self.need_remake_mail_files = self.need_remake_unix_files = False
        if DOMS_CMDS[verb](data):
            self.check_remake_files()
            return True
        else:
            log.log(f"ERROR: cmd '{verb}' failed")
            return False

    def password_changed(self, data):
        self.need_remake_unix_files = True
        return True

    def account_closed(self, data):
        if data is not None and isinstance(data, dict) and (user := data.get(
                "user", None)) is not None:
            self.delete_user(user)
            return True
        return False

    def find_user_by_email(self, email):
        for user in self.all_users:
            if self.all_users[user].get("email", "") == email:
                return user
        return None

    def request_password_reset(self, data):
        email = data.get("email", None)
        pin = data.get("pin", None)
        if email is None or pin is None:
            return False
        if (user := self.find_user_by_email(email)) is None:
            return False

        reset_url_code = misc.make_session_code(user["user"])
        store_code = misc.make_hash(reset_url_code + ":" + pin)

        with open(os.path.join(policy.RESET_CODES, store_code), "w") as fd:
            fd.write(f'{ "user" : {user} }')

        ok, reply = uconfig.update(
            user, {"event": {
                "desc": "Password reset request"
            }},
            with_events=False)
        if ok:
            self.all_users[user] = reply

        return sendmail.post("request_password_reset", {
            "user": self.all_users[user],
            "reset_url_code": reset_url_code
        })


def test_test(data):
    log.log(
        f"TEST DOMS: {data}, Users: {len(Users.all_users)}, Active: {len(Users.active_users)}"
    )
    return True


Users = UserData()

DOMS_CMDS = {
    "new_user_added": Users.new_user_added,
    "identity_changed": Users.identity_changed,
    "email_users_welcome": Users.email_users_welcome,
    "user_age_check": Users.user_age_check,
    "run_mx_check": Users.run_mx_check,
    "remake_unix_files": Users.remake_unix_files_true,
    "remake_mail_files": Users.remake_mail_files_true,
    "start_up_new_files": Users.start_up_new_files,
    "password_changed": Users.password_changed,
    "account_closed": Users.account_closed,
    "request_password_reset": Users.request_password_reset,
    "test": test_test
}


def runner(with_debug, to_syslog):
    log.init("DOMS backend",
             with_debug=(with_debug or misc.debug_mode()),
             to_syslog=to_syslog)

    Users.finish_start_uo()
    log.log("DOMS backend running")

    while True:
        if (file := executor.find_oldest_cmd("doms")) is None:
            time.sleep(1)
        else:
            with open(file, "r") as fd:
                cmd_data = json.load(fd)
            os.remove(file)
            if "verb" not in cmd_data:
                log.log(f"ERROR: 'verb' missing from '{cmd_data}' data")
            elif cmd_data["verb"] not in DOMS_CMDS:
                log.log(f"ERROR: Verb '{cmd_data['verb']}' is not supported")
            else:
                log.debug(f"Running cmd: '{cmd_data['verb']}'")
                if not Users.dispatch_job(cmd_data["verb"],
                                          cmd_data.get("data", None)):
                    time.sleep(5)


def run_tests():
    Users.startup()
    print({
        dom: Users.all_users[user]["domains"][dom]
        for user in Users.active_users
        for dom in Users.all_users[user].get("domains", {})
    })
    print({
        dom: True
        for user in Users.active_users
        for dom in Users.all_users[user].get("domains", {})
        if Users.all_users[user]["domains"][dom]
    })


def main():
    parser = argparse.ArgumentParser(description='DOMS Jobs Runner')
    parser.add_argument("-D",
                        "--debug",
                        default=False,
                        help="With debug messages",
                        action="store_true")
    parser.add_argument("-S",
                        "--syslog",
                        default=False,
                        help="With syslog",
                        action="store_true")
    parser.add_argument("-T",
                        "--test",
                        default=False,
                        help="Run tests",
                        action="store_true")
    parser.add_argument("-O", "--one", help="Run one module")
    parser.add_argument("-d", "--data", help="data for running one")
    args = parser.parse_args()

    Users.startup()
    if args.one:
        log.init("DOMS run one",
                 with_debug=misc.debug_mode(),
                 to_syslog=args.syslog)
        if args.one not in DOMS_CMDS:
            log.log(f"ERROR: DOMS CMD '{args.one}' not valid")
            return
        Users.dispatch_job(args.one,
                           json.loads(args.data) if args.data else None)

    elif args.test:
        log.init("DOMS run test", with_debug=args.debug, to_syslog=args.syslog)
        run_tests()

    else:
        runner(args.debug, args.syslog)


if __name__ == "__main__":
    main()
