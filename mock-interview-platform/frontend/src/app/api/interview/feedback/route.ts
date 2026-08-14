/**
 * ⚠️ DEPRECATED - This API route is dead code and should not be used
 *
 * This was an early reference implementation for calling Gemini directly from the frontend.
 * The live application uses the Flask backend instead.
 *
 * LIVE IMPLEMENTATION:
 * - POST /api/interview/analyze-answer (via Flask backend at NEXT_PUBLIC_API_URL)
 * - Backend handles Gemini integration, NLP analysis, CV analysis, feedback generation
 * - Responses are persisted to MongoDB with interview metadata
 *
 * DEAD CODE:
 * - This route exposes GEMINI_API_KEY to the browser (security risk)
 * - No rate limiting or usage enforcement
 * - No data persistence
 * - No integration with subscription/billing system
 * - No CV/expression analysis (only Gemini feedback)
 *
 * Do NOT use this route. It is kept here temporarily for reference during cleanup.
 * TODO: Delete frontend/src/app/api/interview/ directory entirely
 */

import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  return NextResponse.json(
    {
      error: "DEPRECATED: This API route is dead code. Use the Flask backend instead.",
      details: "POST /api/interview/analyze-answer via NEXT_PUBLIC_API_URL",
      see: "backend/app/routes/interview.py for the real implementation"
    },
    { status: 410 } // 410 Gone - resource no longer available
  );
}
      );
    }

    if (qaPairs.some((p: { answer?: string }) => !p.answer?.trim())) {
      return NextResponse.json(
        { error: "Every question needs a non-empty answer before requesting feedback" },
        { status: 400 }
      );
    }

    const transcript = qaPairs
      .map((p: { question: string; answer: string }, i: number) => `Q${i + 1}: ${p.question}\nA${i + 1}: ${p.answer}`)
      .join("\n\n");

    const response = await ai.models.generateContent({
      model: "gemini-flash-latest",
      contents: `You are a hiring manager reviewing a mock interview for a ${role} role. Evaluate each answer below.\n\n${transcript}`,
      config: {
        responseMimeType: "application/json",
        responseJsonSchema: {
          type: Type.OBJECT,
          properties: {
            overallScore: { type: Type.INTEGER, description: "0-100" },
            overallSummary: { type: Type.STRING },
            perQuestion: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  question: { type: Type.STRING },
                  score: { type: Type.INTEGER },
                  strengths: { type: Type.ARRAY, items: { type: Type.STRING } },
                  improvements: { type: Type.ARRAY, items: { type: Type.STRING } },
                },
                propertyOrdering: ["question", "score", "strengths", "improvements"],
              },
            },
          },
          propertyOrdering: ["overallScore", "overallSummary", "perQuestion"],
        },
      },
    });

    if (response.candidates?.[0]?.finishReason === "SAFETY") {
      return NextResponse.json(
        { error: "Feedback generation blocked by safety filters" },
        { status: 422 }
      );
    }

    return NextResponse.json({ data: JSON.parse(response.text) });
  } catch (error) {
    console.error("Gemini feedback error:", error);
    const message = error instanceof Error ? error.message : "Failed to generate feedback";
    return NextResponse.json(
      { error: message },
      { status: 500 }
    );
  }
}
