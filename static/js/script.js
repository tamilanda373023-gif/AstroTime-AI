document.addEventListener("DOMContentLoaded", function () {
    const mapElement = document.getElementById('map');
    if (mapElement) {
        const map = L.map('map').setView([4.2105, 101.9758], 6);

        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);

        let marker = L.marker([4.2105, 101.9758], { draggable: true }).addTo(map);

        function updateCoordinates(lat, lng) {
            document.getElementById('latitude').value = lat.toFixed(6);
            document.getElementById('longitude').value = lng.toFixed(6);
        }

        map.on('click', function (e) {
            const lat = e.latlng.lat;
            const lng = e.latlng.lng;
            marker.setLatLng(e.latlng);
            updateCoordinates(lat, lng);
        });

        marker.on('dragend', function (e) {
            const position = marker.getLatLng();
            updateCoordinates(position.lat, position.lng);
        });
    }
});