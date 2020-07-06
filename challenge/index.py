import os
import json
import pika
import hashlib
import binascii
import functools
import mimetypes
from os import path
from urllib import parse
from datetime import timedelta
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_pymongo import PyMongo
from urllib.parse import urlparse, urljoin
from pymongo.errors import DuplicateKeyError
from flask_behind_proxy import FlaskBehindProxy
from flask import Flask, render_template, request, session, flash, jsonify, redirect, url_for

__folder__ = path.abspath(path.dirname(__file__))

STICKY_COOKIE_NAME = os.environ.get("STICKY_COOKIE_NAME", "")
RABITMQ_HOST = os.environ.get("RABITMQ_HOST", "queue")
RABITMQ_PORT = int(os.environ.get("RABITMQ_PORT", 5672))
CHALLENGE_URL = os.environ.get("CHALLENGE_URL", "https://bugler.ctf.bsidestlv.com/")

app = Flask(__name__, static_folder="public", template_folder="views", static_url_path="/")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=int(os.environ.get("PERMANENT_SESSION_LIFETIME", 15)))
app.config['SESSION_COOKIE_SAMESITE'] = "Lax"
app.config['SESSION_COOKIE_SECURE'] = True
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(16))
app.config["MONGO_URI"] = os.environ.get("MONGO_URI", "mongodb://database:27017/bugler")
mongo = PyMongo(app)
mongo.db.users.create_index("id", unique=True)
mongo.db.users.create_index("username", unique=True)
bcrypt = Bcrypt(app)
limiter = Limiter(
    app,
    key_func=lambda: session.get("user", {}).get("id"),
)
FlaskBehindProxy(app)
mimetypes.add_type('application/javascript', '.js')


def generate_test_id(size=16):
    return binascii.hexlify(os.urandom(size // 2)).decode()


def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user") is None:
            # return redirect(f"/login?next={request.path}")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)

    return decorated_function


# def non_login_required(f):
#     @functools.wraps(f)
#     def decorated_function(*args, **kwargs):
#         if session.get("user") is not None:
#             return redirect(url_for("index"))
#         return f(*args, **kwargs)
#
#     return decorated_function


@app.after_request
def add_headers(response):
    response.headers['Service-Worker-Allowed'] = '/'
    return response


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/logout')
def logout():
    session['user'] = None
    session.clear()
    res = redirect(url_for("index"))
    # res.set_cookie("session", expires=0)
    return res


@app.route('/login', methods=["GET", "POST"])
# @non_login_required
def login():
    if request.method == "POST":
        user = mongo.db.users.find_one({"username": request.form["username"]})
        if not user:
            flash("Wrong username or password")
            return render_template("login.html")

        res = bcrypt.check_password_hash(user["password"], request.form["password"])
        if res:
            session["user"] = {
                "id": user["id"],
                "email": user["email"],
                "username": request.form["username"],
                "avatar": user.get("avatar")
            }
            session.permanent = True
            next_url = urlparse(parse.unquote(request.args.get("next") or "/")).path
            return redirect(next_url)

        flash("Wrong username or password")
    return render_template("login.html")


@app.route('/register', methods=["GET", "POST"])
# @non_login_required
def register():
    if request.method == "POST":
        if len(request.form["password"]) < 7:
            flash("Password length should be bigger then 7")
            return render_template("register.html")

        try:
            user_id = generate_test_id(size=16)
            inserted_id = mongo.db.users.insert_one({
                "id": user_id,
                "username": request.form["username"],
                "password": bcrypt.generate_password_hash(request.form["password"]),
                "email": request.form["email"],
            }).inserted_id

            if inserted_id:
                session["user"] = {
                    "id": user_id,
                    "email": request.form["email"],
                    "username": request.form["username"],
                    "avatar": ""
                }
                return redirect(url_for("index"))
        except DuplicateKeyError:
            flash("User already exist")

    return render_template("register.html")


@app.route('/profile', methods=["GET", "POST"])
@login_required
def current_profile():
    if request.method == "POST":
        update = {}
        for key in ["first_name", "last_name", "email", "website", "address", "city", "state", "username"]:
            value = request.form.get(key)
            if value:
                update[key] = value

        password = request.form.get("password")
        if password:
            update["password"] = bcrypt.generate_password_hash(password)

        avatar = request.files.get("avatar")
        user_dir = path.join(__folder__, "public", "upload", session["user"]["id"])
        if avatar:
            avatar_file_ext = ""
            filename = path.split(avatar.filename)[-1]
            if "." in filename:
                avatar_file_ext = path.splitext(filename)[-1]
            if avatar_file_ext.lower() in [".htm", ".html", ".xhtml", ".xml", ".svg",
                                           ".pdf", ".php", ".py", ".exe", ".dll", ".so"]:
                flash(f"bad file extension: {avatar_file_ext}")
                user = mongo.db.users.find_one_or_404({"id": session["user"]["id"]})
                return render_template("profile.html", user=user, current_user=True)

            os.makedirs(user_dir, exist_ok=True)
            content = avatar.read()
            avatar_file_name = f"{hashlib.md5(content).hexdigest()}{avatar_file_ext}"
            with open(path.join(user_dir, avatar_file_name), "wb") as f:
                f.write(content)
                f.flush()
            update["avatar"] = f"/upload/{session['user']['id']}/{avatar_file_name}"

        mongo.db.users.find_one_and_update({"id": session["user"]["id"]}, {"$set": update})
        user = mongo.db.users.find_one({"id": session["user"]["id"]})
        session["user"] = {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "avatar": user.get("avatar")
        }

    user = mongo.db.users.find_one_or_404({"id": session["user"]["id"]})
    return render_template("profile.html", user=user, current_user=True)


@app.route('/profile/<string:user_id>')
@login_required
def profile(user_id):
    # admin = mongo.db.users.find_one({"username": "admin"})
    # if admin and user_id not in [admin["id"], session["user"]["id"]]:
    #     return abort(404)

    user = mongo.db.users.find_one_or_404({"id": user_id})
    return render_template("profile.html", user=user, current_user=False)


@app.route('/report/<string:user_id>')
@limiter.limit("5/minute", override_defaults=False)
@login_required
def report(user_id):
    user = mongo.db.users.find_one_or_404({"id": user_id})
    website = urlparse(user.get("website") or "")
    website_protocol = website.scheme
    website_hostname = website.hostname
    reported = False
    if website_protocol and website_protocol in ["http", "https"] \
            and website_hostname and urlparse(CHALLENGE_URL).hostname != website_hostname:
        reported = True
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABITMQ_HOST, port=RABITMQ_PORT))
            channel = connection.channel()
            channel.queue_declare(queue='browser')
            channel.basic_publish(exchange='', routing_key='browser', body=json.dumps({
                "actions": [
                    # Open User URL
                    {"action": "page.goto", "args": [
                        user["website"],
                        {'timeout': 3000, "waitUntil": 'domcontentloaded'}
                    ]},
                    # Wait 3 Seconds
                    {"action": "page.waitFor", "args": [3000]},
                    # Close all pages
                    {"action": "context.closePages", "args": []},
                    # Login
                    {"action": "page.goto", "args": [
                        urljoin(CHALLENGE_URL, "/login"),
                        {'timeout': 3000, "waitUntil": 'domcontentloaded'}
                    ]},
                    {"action": "page.type", "args": ["#exampleInputUsername", "admin"]},
                    {
                        "action": "page.type",
                        "args": ["#exampleInputPassword", "BSidesTLV2020{S3rv1ce_W0rk3rs@Y0urS3rvic3}"]
                    },
                    {"action": "page.click", "args": ["#signin"]},
                    {"action": "page.waitFor", "args": [1000]},
                ]
            }))
            connection.close()
        except Exception as ex:
            reported = False
            print(ex)

    return jsonify({
        "reported": reported
    })


if __name__ == '__main__':
    app.run(host="0.0.0.0", port="443", ssl_context=("ssl/server.crt", "ssl/server.key"), threaded=True)
