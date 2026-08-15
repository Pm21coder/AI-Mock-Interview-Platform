/**
 * This frontend API route has been retired. The Flask backend owns interview
 * question generation at /api/interview/generate-questions.
 */
import { NextResponse } from "next/server";

export async function POST() {
  return NextResponse.json(
    {
      error: "DEPRECATED: This API route is no longer available. Use the Flask backend instead.",
      details: "POST /api/interview/generate-questions via NEXT_PUBLIC_API_URL",
      see: "backend/app/routes/interview.py for the active implementation",
    },
    { status: 410 }
  );
}
