#!/usr/bin/env node

const amqplib = require("amqplib");
const puppeteer = require("puppeteer");

let config = require("./config");

const RABITMQ_HOST = process.env.RABITMQ_HOST || config.queue.host;
const RABITMQ_PORT = parseInt(process.env.RABITMQ_PORT || config.queue.port);

const QUEUE_NAME = process.env.RABITMQ_PORT || config.queue.name;
const allowed_actions = config.allowed_actions;

function sleep(time = 1000) {
    return new Promise(resolve => {
        setTimeout(() => {
            return resolve();
        }, time);
    });
}

(async () => {
    let connection = null;
    while (!connection) {
        try {
            connection = await amqplib.connect({
                protocol: 'amqp',
                maxLength: 1,
                hostname: RABITMQ_HOST,
                port: RABITMQ_PORT,
            });
        } catch (error) {
            console.error(error);
            await sleep();
        }
    }

    const channel = await connection.createChannel();
    await channel.assertQueue(QUEUE_NAME, {
        durable: false
    });
    await channel.prefetch(1);
    await channel.consume(QUEUE_NAME, async function (msg) {
        console.debug("\n[x] Received %s", msg.content.toString());
        const data = JSON.parse(msg.content.toString());

        this.browser = await puppeteer.launch(config.browser.options);
        this.page = await this.browser.newPage();
        for (let [event_name, event] of Object.entries(config.page.events)) {
            this.page.on(event_name, event);
        }
        await this.page.evaluateOnNewDocument(`(${config.page.evaluate.document_start.toString()})();`);

        // Add close pages function
        const me = this;
        this.browser.closePages = async function () {
            for (let page of await me.browser.pages()) {
                await page.close();
            }
            me.page = await me.browser.newPage();
        };

        try {
            for (let {action, args, is_async = true} of data['actions']) {
                if (!allowed_actions.includes(action)) {
                    console.warn(`the action ${action} was not allowed`);
                    continue;
                }
                console.log(`${action}(${JSON.stringify(args).replace(/(^\[|]$)/g, '')})`);
                const [objectName, funcName] = action.split('.');
                const object = this[objectName];
                const func = object[funcName];
                if (is_async) {
                    await func.apply(object, args);
                    continue;
                }
                func.apply(object, args);
            }
        } catch (error) {
            console.error(error);
        }
        await this.browser.close();
        return channel.ackAll();
    });
})();
