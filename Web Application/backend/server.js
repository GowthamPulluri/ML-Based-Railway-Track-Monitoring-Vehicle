const express = require("express");
const http = require("http");
const socketIo = require("socket.io");
const axios = require("axios");
const cors = require("cors");

const app = express();
const server = http.createServer(app);

const io = socketIo(server, {
  cors: { origin: "*" }
});

app.use(cors());
app.use(express.json());

const PORT = 5000;

const SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz5c6s5MCS6WDGJo9ylDRUXgx4BvZeJPCr8VOcGZn-ncKsQdi0V3U2DiGM8enhUkgmW/exec";

// ================= FETCH DEFECTS =================
app.get("/defects", async (req, res) => {
  try {
    const response = await axios.get(SCRIPT_URL + "?action=defects");
    const rows = response.data.defects || [];

    const formatted = rows.slice(1).map(r => ({
      id: r[0],
      time: new Date(r[0]).toLocaleString(),
      rawTime: r[0],
      defect: r[1],
      lat: Number(r[2]),
      lon: Number(r[3]),
      status: r[4]
    }));

    res.json(formatted);

  } catch {
    res.status(500).send("Error");
  }
});

// ================= DELETE =================
app.post("/solve", async (req, res) => {
  const { time } = req.body;

  try {
    await axios.post(SCRIPT_URL, {
      action: "delete",
      time: time
    });

    res.send("Deleted");

  } catch {
    res.status(500).send("Delete failed");
  }
});

// ================= SOCKET =================
io.on("connection", () => {
  console.log("Client connected");
});

// ================= SMART POLLING =================
let lastSentTime = null;

async function pollSheet() {
  try {
    const response = await axios.get(SCRIPT_URL + "?action=defects");
    const rows = response.data.defects || [];

    const formatted = rows.slice(1).map(r => ({
      id: r[0],
      time: new Date(r[0]).toLocaleString(),
      rawTime: r[0],
      defect: r[1],
      lat: Number(r[2]),
      lon: Number(r[3]),
      status: r[4]
    }));

    if (formatted.length > 0) {
      const last = formatted[formatted.length - 1];

      // 🔥 Only emit if NEW defect
      if (last.rawTime !== lastSentTime) {
        lastSentTime = last.rawTime;
        io.emit("defect-update", formatted);
      }
    }

  } catch (err) {
    console.log(err);
  }
}

setInterval(pollSheet, 4000);

server.listen(PORT, () => {
  console.log("Server running on", PORT);
});