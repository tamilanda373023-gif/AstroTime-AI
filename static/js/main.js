function updateHUD() {
    const liveUtc = document.getElementById('live-utc');
    const hudJd = document.getElementById('hud-jd');
    const hudGst = document.getElementById('hud-gst');
    const hudEot = document.getElementById('hud-eot');

    if (!liveUtc) return;

    const now = new Date();
    liveUtc.innerText = now.toUTCString().slice(17, 25) + ' UTC';

    const jd = (now.getTime() / 86400000) + 2440587.5;
    if (hudJd) hudJd.innerText = jd.toFixed(2);

    const hrs = now.getUTCHours(), mins = now.getUTCMinutes(), secs = now.getUTCSeconds();
    if (hudGst) hudGst.innerText = `${String((hrs + 4) % 24).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    if (hudEot) hudEot.innerText = `${(Math.sin(now.getDay()) * 14).toFixed(1)} mins`;
}

document.addEventListener('DOMContentLoaded', () => {
    setInterval(updateHUD, 1000);
    updateHUD();
});