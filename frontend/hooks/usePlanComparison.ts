"use client";

import { useEffect, useRef, useState } from "react";
import {
  Room,
  RoomEvent,
  DataPacket_Kind,
  ConnectionState,
} from "livekit-client";

export interface Citation {
  pdf_url: string;
  page: number;
  left: number;
  top: number;
  width: number;
  height: number;
  source_text: string;
}

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
  citations: Citation[];
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
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    async function connect() {
      if (cancelled) return;

      // Check if the room exists before attempting to connect.
      // This prevents the browser from creating amparo-demo prematurely,
      // which would block the SIP dispatch from triggering the agent.
      try {
        const statusRes = await fetch("/api/room-status");
        if (statusRes.ok) {
          const { exists } = await statusRes.json();
          if (!exists) {
            setStatus("disconnected");
            retryTimer = setTimeout(connect, 3000);
            return;
          }
        }
      } catch {
        setStatus("disconnected");
        retryTimer = setTimeout(connect, 3000);
        return;
      }

      if (cancelled) return;
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
          else if (state === ConnectionState.Disconnected) {
            setStatus("disconnected");
            // Reconnect if the call ends and a new one comes in
            retryTimer = setTimeout(connect, 3000);
          }
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

        await room.connect(livekitUrl, token, { autoSubscribe: true });
      } catch (err: unknown) {
        if (cancelled) return;
        console.error("LiveKit connect error:", err);
        setStatus("disconnected");
        retryTimer = setTimeout(connect, 3000);
      }
    }

    connect();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      roomRef.current?.disconnect();
      roomRef.current = null;
    };
  }, [livekitUrl]);

  return { status, comparison, totalLookups };
}
