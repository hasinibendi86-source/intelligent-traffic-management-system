import { Routes, Route, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import LiveTraffic from "./pages/LiveTraffic.jsx";
import SignalOptimization from "./pages/SignalOptimization.jsx";
import Analytics from "./pages/Analytics.jsx";
import Alerts from "./pages/Alerts.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/live-traffic" element={<LiveTraffic />} />
      <Route path="/signal-optimization" element={<SignalOptimization />} />
      <Route path="/analytics" element={<Analytics />} />
      <Route path="/alerts" element={<Alerts />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
