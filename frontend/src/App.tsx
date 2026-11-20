import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Alerts from "./pages/Alerts";
import Ask from "./pages/Ask";
import Explorer from "./pages/Explorer";
import Health from "./pages/Health";
import Overview from "./pages/Overview";
import Parity from "./pages/Parity";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/explorer" element={<Explorer />} />
        <Route path="/parity" element={<Parity />} />
        <Route path="/ask" element={<Ask />} />
        <Route path="/health" element={<Health />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
