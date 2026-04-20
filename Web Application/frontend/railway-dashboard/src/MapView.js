import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";

const trainIcon = new L.Icon({
  iconUrl: "https://cdn-icons-png.flaticon.com/512/713/713311.png",
  iconSize: [40, 40]
});

const defectIcon = new L.Icon({
  iconUrl: "https://cdn-icons-png.flaticon.com/512/252/252025.png",
  iconSize: [30, 30]
});

// ================= AUTO MOVE MAP =================
function FlyTo({ loc }) {
  const map = useMap();

  if (loc) {
    map.flyTo([loc.lat, loc.lon], 16);
  }

  return null;
}

function MapView({ defects, selected }) {

  const latest = defects.length > 0 ? defects[defects.length - 1] : null;

  return (
    <MapContainer
      center={[17.731438, 83.301616]}
      zoom={14}
      style={{ height: "500px" }}
    >

      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

      {/* 🚆 Train (latest position) */}
      {latest && (
        <Marker position={[latest.lat, latest.lon]} icon={trainIcon}>
          <Popup>
            🚆 Train Location <br />
            📍 {latest.lat}, {latest.lon}
          </Popup>
        </Marker>
      )}

      {/* ⚠️ Selected defect */}
      {selected && (
        <Marker position={[selected.lat, selected.lon]} icon={defectIcon}>
          <Popup>
            🚨 {selected.defect} <br />
            📍 {selected.lat}, {selected.lon}
          </Popup>
        </Marker>
      )}

      {/* Auto move */}
      <FlyTo loc={selected || latest} />

    </MapContainer>
  );
}

export default MapView;