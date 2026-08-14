/**
 * ⚠️ DEPRECATED - This API route is dead code and should not be used
 *
 * This was an early reference implementation for calling Gemini directly from the frontend.
 * The live application uses the Flask backend instead.
 *
 * LIVE IMPLEMENTATION:
 * - POST /api/interview/generate-questions (via Flask backend at NEXT_PUBLIC_API_URL)
 * - Backend handles Gemini integration, authentication, usage tracking
 * - Questions are persisted to MongoDB with interview session metadata
 *
 * DEAD CODE:
 * - This route exposes GEMINI_API_KEY to the browser (security risk)
 * - No rate limiting or usage enforcement
 * - No data persistence
 * - Not integrated with subscription system
 *
 * Do NOT use this route. It is kept here temporarily for reference during cleanup.
 * TODO: Delete frontend/src/app/api/interview/ directory entirely
 */

import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  return NextResponse.json(
    {
      error: "DEPRECATED: This API route is dead code. Use the Flask backend instead.",
      details: "POST /api/interview/generate-questions via NEXT_PUBLIC_API_URL",
      see: "backend/app/routes/interview.py for the real implementation"
    },
    { status: 410 } // 410 Gone - resource no longer available
  );
}
      return NextResponse.json(
        { error: "Blocked by safety filters — try a different role/category" },
        { status: 422 }
      );
    }

    const data = JSON.parse(response.text);
    return NextResponse.json({ data: data.questions });
  } catch (error) {
    console.error("Gemini question generation error:", error);
    const message = error instanceof Error ? error.message : "Failed to generate questions";
    return NextResponse.json(
      { error: message },
      { status: 500 }
    );
  }
}
