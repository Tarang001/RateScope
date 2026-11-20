export type Hotel = {
  id: number;
  name: string;
  city: string;
  country: string;
  star_rating: number;
};

export type Room = {
  id: number;
  hotel_id: number;
  room_type: string;
  cancellation_policy: string;
  occupancy: number;
};

export type AlertItem = {
  id: number;
  alert_type: string;
  severity: string;
  status: string;
  hotel_id: number;
  room_id: number;
  stay_date: string;
  city: string;
  supplier_codes: string[];
  title: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  hotel_name?: string;
};

export type Overview = {
  hotels: number;
  suppliers: number;
  events_processed: number;
  active_alerts: number;
  dlq_count: number;
  recent: Array<{
    id: number;
    hotel_id: number;
    city: string;
    price_usd: number;
    stay_date: string;
    received_at: string;
    scenario: string;
  }>;
};

export type PricePoint = {
  received_at: string;
  stay_date: string;
  supplier_code: string;
  price_usd: number;
  availability: number;
  scenario: string;
};

export type SystemHealth = {
  status: string;
  postgres: boolean;
  redis: boolean;
  kafka: boolean;
  events_processed: number;
  dlq_count: number;
  consumer_lag: number;
  processing_latency_ms: number;
  api_health: string;
};
