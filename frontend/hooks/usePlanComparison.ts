"use client";

import { useEffect, useRef, useState } from "react";
import {
  Room,
  RoomEvent,
  DataPacket_Kind,
  ConnectionState,
} from "livekit-client";

export interface CostResult {
  plan_id: string;
  plan_name: string;
  annual_premium: number;
  covered_oop: number;
  capped_covered_oop: number;
  uncovered_costs: number;
  annual_total: number;
  trap_flag: boolean;
  uncovered_drugs: string[];
  out_of_network_providers: string[];
  sources: string[];
}

export interface PlanComparisonData {
  plans: CostResult[];
  lookup_count: number;
  trap: boolean;
  trap_plan_id: string | null;
  timestamp: number;
}

type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

export function usePlanComparison(livekitUrl: string) {
  const roomRef = useRef<Room | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [comparison, setComparison] = useState<PlanComparisonData | null>(null);
  const [totalLookups, setTotalLookups] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function connect() {
      setStatus("connecting");

      try {
        const res = await fetch("/api/token");
        if (!res.ok) throw new Error("Failed to fetch token");
        const { token } = await res.json();
        if (cancelled) return;

        const room = new Room();
        roomRef.current = room;

        room.on(RoomEvent.ConnectionStateChanged, (state) => {
          if (state === ConnectionState.Connected) setStatus("connected");
          else if (state === ConnectionState.Disconnected) setStatus("disconnected");
        });

        room.on(RoomEvent.DataReceived, (payload: Uint8Array) => {
          try {
            const text = new TextDecoder().decode(payload);
            const msg = JSON.parse(text);
            if (msg.type === "plan_comparison" && msg.data) {
              const data: PlanComparisonData = msg.data;
              setComparison(data);
              setTotalLookups((prev) => prev + data.lookup_count);
            }
          } catch {
            // ignore malformed messages
          }
        });

        await room.connect(livekitUrl, token, {
          autoSubscribe: true,
        });
      } catch (err) {
        console.error("LiveKit connect error:", err);
        if (!cancelled) setStatus("error");
      }
    }

    connect();

    return () => {
      cancelled = true;
      roomRef.current?.disconnect();
      roomRef.current = null;
    };
  }, [livekitUrl]);

  return { status, comparison, totalLookups };
}
