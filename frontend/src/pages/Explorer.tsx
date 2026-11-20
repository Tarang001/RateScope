import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Empty, ErrorBox, Loading } from "../components/States";
import { api } from "../services/api";
import type { Hotel, PricePoint, Room } from "../types";

const COLORS: Record<string, string> = { AGODA: "#14b8a6", BOOKING: "#3b82f6", EXPEDIA: "#f59e0b" };

export default function Explorer() {
  const [hotels, setHotels] = useState<Hotel[]>([]);
  const [city, setCity] = useState("Delhi");
  const [hotelId, setHotelId] = useState<number | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [roomId, setRoomId] = useState<number | null>(null);
  const [stayDate, setStayDate] = useState("");
  const [points, setPoints] = useState<PricePoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.hotels().then(setHotels).catch((e) => setError(e.message));
  }, []);

  const cities = useMemo(() => Array.from(new Set(hotels.map((h) => h.city))), [hotels]);
  const cityHotels = hotels.filter((h) => h.city === city);

  useEffect(() => {
    if (cityHotels.length && !cityHotels.some((h) => h.id === hotelId)) {
      setHotelId(cityHotels[0].id);
    }
  }, [city, hotels]);

  useEffect(() => {
    if (!hotelId) return;
    api.hotelRates(hotelId, stayDate || undefined).then((r) => {
      setRooms(r.rooms);
      if (r.rooms.length) setRoomId(r.rooms[0].id);
    });
  }, [hotelId, stayDate]);

  useEffect(() => {
    if (!roomId) return;
    setLoading(true);
    api
      .priceHistory(roomId, stayDate || undefined)
      .then((r) => setPoints(r.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [roomId, stayDate]);

  const chartData = useMemo(() => {
    const byTime: Record<string, Record<string, number | string>> = {};
    points.forEach((p) => {
      const t = p.received_at.slice(11, 19) || p.received_at;
      byTime[t] = byTime[t] || { t };
      byTime[t][p.supplier_code] = p.price_usd;
    });
    return Object.values(byTime);
  }, [points]);

  const anomalies = points.filter((p) => p.scenario === "PRICE_SPIKE" || p.scenario === "PRICE_DROP" || p.scenario === "PARITY_BREAK");

  if (error) return <ErrorBox message={error} />;

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold">Price Explorer</h2>
      <div className="grid gap-3 md:grid-cols-4">
        <select className="card py-2" value={city} onChange={(e) => setCity(e.target.value)}>
          {cities.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
        <select className="card py-2" value={hotelId ?? ""} onChange={(e) => setHotelId(Number(e.target.value))}>
          {cityHotels.map((h) => (
            <option key={h.id} value={h.id}>
              {h.name}
            </option>
          ))}
        </select>
        <select className="card py-2" value={roomId ?? ""} onChange={(e) => setRoomId(Number(e.target.value))}>
          {rooms.map((r) => (
            <option key={r.id} value={r.id}>
              {r.room_type} · {r.cancellation_policy}
            </option>
          ))}
        </select>
        <input className="card py-2" type="date" value={stayDate} onChange={(e) => setStayDate(e.target.value)} />
      </div>
      {loading && <Loading label="Loading history" />}
      {!loading && points.length === 0 && <Empty title="No observations yet" hint="Pick another room or wait for simulation." />}
      {chartData.length > 0 && (
        <div className="card h-96">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="t" />
              <YAxis />
              <Tooltip />
              <Legend />
              {["AGODA", "BOOKING", "EXPEDIA"].map((s) => (
                <Line key={s} type="monotone" dataKey={s} stroke={COLORS[s]} dot={false} connectNulls />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      {anomalies.length > 0 && (
        <div className="card">
          <h3 className="mb-2 font-medium">Highlighted scenarios</h3>
          <ul className="text-sm space-y-1">
            {anomalies.slice(-8).map((p, i) => (
              <li key={i}>
                {p.supplier_code} {p.scenario} @ ${p.price_usd.toFixed(0)} ({p.received_at})
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
