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
        "context.closePages"
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
            // "console": message => console.debug(`[${message.type().toUpperCase()}] ${message.text()}`),
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
