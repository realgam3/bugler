module.exports = {
    "queue": {
        "host": "queue",
        "port": 5672,
        "name": "browser"
    },
    "allowed_actions": [
        "page.goto",
        "page.waitFor",
        "page.type",
        "page.click",
        "browser.closePages"
    ],
    "browser": {
        "options": {
            "headless": true,
            "ignoreHTTPSErrors": true,
            "args": [
                "--disable-gpu",
                "--no-sandbox",
                "--ignore-certificate-errors"
            ]
        }
    },
    "page": {
        "events": {
            "pageerror": message => console.error(message),
            "error": message => console.error(message),
        },
        "evaluate": {
            "document_start": function () {
                window.open = () => {
                    console.warn("window.open");
                };
            }
        }
    }
};
