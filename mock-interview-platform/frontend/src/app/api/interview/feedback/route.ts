import { GoogleGenAI, Type } from "@google/genai";
import { NextRequest, NextResponse } from "next/server";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

export async function POST(req: NextRequest) {
  if (!process.env.GEMINI_API_KEY) {
    return NextResponse.json(
      { error: "Server misconfigured: missing GEMINI_API_KEY" },
      { status: 500 }
    );
  }

  try {
    const { role, qaPairs } = await req.json();

    if (!Array.isArray(qaPairs) || qaPairs.length === 0) {
      return NextResponse.json(
        { error: "qaPairs must be a non-empty array" },
        { status: 400 }
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
