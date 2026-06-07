import { AccessToken } from "livekit-server-sdk";
import { NextResponse } from "next/server";

const ROOM = "amparo-demo";

export async function GET() {
  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;

  if (!apiKey || !apiSecret) {
    return NextResponse.json(
      { error: "LiveKit credentials not configured" },
      { status: 500 }
    );
  }

  const at = new AccessToken(apiKey, apiSecret, {
    identity: `panel-observer-${Date.now()}`,
    ttl: "4h",
  });

  // Subscriber-only observer: cannot create the room (prevents stale-room dispatch issue).
  // The SIP call creates amparo-demo; the panel joins after.
  at.addGrant({
    roomJoin: true,
    roomCreate: false,
    room: ROOM,
    canSubscribe: true,
    canPublish: false,
    canPublishData: false,
  });

  const token = await at.toJwt();
  return NextResponse.json({ token });
}
