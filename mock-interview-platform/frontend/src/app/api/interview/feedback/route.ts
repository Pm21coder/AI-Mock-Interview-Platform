/**
 * This frontend API route has been retired. The Flask backend owns interview
 * feedback generation at /api/interview/analyze-answer.
 */
import { NextResponse } from "next/server";

export async function POST() {
  return NextResponse.json(
    {
      error: "DEPRECATED: This API route is no longer available. Use the Flask backend instead.",
      details: "POST /api/interview/analyze-answer via NEXT_PUBLIC_API_URL",
      see: "backend/app/routes/interview.py for the active implementation",
    },
    { status: 410 }
  );
}
