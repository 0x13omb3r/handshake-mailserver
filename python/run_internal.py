#! /usr/bin/python3
# (c) Copyright 2019-2020, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import flask

import from_email_allowed


application = flask.Flask("internal/api")


def return_resp(data, code):
    resp = flask.make_response(flask.jsonify(data), 200)
    resp.charset = 'utf-8'
    return resp


def abort(message):
    return return_resp({"result": "BAD", "error": message}, 499)


def worked(message):
    return return_resp({"result": "OK", "message": message}, 200)


@application.route("/internal/hello", methods=["GET"])
def hello():
    return flask.jsonify({"Hello": "world"})


@application.route("/internal/check/sender", methods=["POST", "GET"])
def check_sender():
    js = flask.request.json if flask.request.method == "POST" and flask.request.is_json else None
    if js is None or len(js) <= 0:
        js = flask.request.values if flask.request.method == "GET" and len(
            flask.request.values) > 0 else None
        if js is None or len(js) <= 0:
            return abort("No data")

    user = js.get("user", None)
    email = js.get("email", None)
    if user is None or email is None:
        return abort("User or email missing or blank")

    ok, reply = from_email_allowed.is_allowed_email(user, email)
    if not ok:
        return abort(reply)
    return worked(reply)


if __name__ == "__main__":
    application.run()
