import { RoomServiceClient } from "livekit-server-sdk";
import { NextResponse } from "next/server";

const ROOM = "amparo-demo";

export async function GET() {
  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;
  const livekitUrl = process.env.LIVEKIT_URL;

  if (!apiKey || !apiSecret || !livekitUrl) {
    return NextResponse.json({ exists: false, error: "Not configured" });
  }

  try {
    const svc = new RoomServiceClient(livekitUrl, apiKey, apiSecret);
    const rooms = await svc.listRooms([ROOM]);
    const exists = rooms.some((r) => r.name === ROOM);
    return NextResponse.json({ exists });
  } catch {
    return NextResponse.json({ exists: false });
  }
}
