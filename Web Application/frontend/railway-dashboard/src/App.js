import { useEffect, useState, useRef } from "react";
import io from "socket.io-client";
import axios from "axios";
import MapView from "./MapView";
import "./App.css";
import toast, { Toaster } from "react-hot-toast";

const socket = io("http://localhost:5000");

function App() {

  const [defects, setDefects] = useState([]);
  const [selected, setSelected] = useState(null);

  const lastNotified = useRef(null);

  useEffect(() => {

    loadInitial();

    // 🔥 REMOVE previous listeners (IMPORTANT)
    socket.off("defect-update");

    // 🔥 ADD fresh listener
    socket.on("defect-update", data => {

      setDefects(data);

      if (data.length > 0) {
        const last = data[data.length - 1];

        if (lastNotified.current !== last.rawTime) {
          lastNotified.current = last.rawTime;
          toast.error(`🚨 ${last.defect}`);
        }
      }

    });

    // 🔥 CLEANUP on unmount
    return () => {
      socket.off("defect-update");
    };

  }, []);

  const loadInitial = async () => {
    const res = await axios.get("http://localhost:5000/defects");
    setDefects(res.data);
  };

  const clearIssue = async (d) => {

    await axios.post("http://localhost:5000/solve", {
      time: d.rawTime
    });

    setDefects(prev => prev.filter(x => x.id !== d.id));

    toast.success("Cleared");
  };

  return (
    <div className="dashboard">

      <Toaster />
      <h1 className="mainTitle" style={{ textAlign: "center" }}>
        Smart Railway Monitoring System Dashboard
      </h1>

      <div className="card">
        <h2>Defect Logs</h2>

        <table className="logTable">
          <thead>
            <tr>
              <th>Time</th>
              <th>Defect</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {defects.map(d => (
              <tr key={d.id}>
                <td>{d.time}</td>
                <td>{d.defect}</td>
                <td>{d.status}</td>

                <td>
                  <button onClick={() => setSelected(d)}>
                    Locate
                  </button>

                  <button
                    className="solveBtn"
                    onClick={() => clearIssue(d)}
                  >
                    Clear
                  </button>
                </td>
              </tr>
            ))}
          </tbody>

        </table>
      </div>

      <MapView defects={defects} selected={selected} />

    </div>
  );
}

export default App;