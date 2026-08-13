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
    const { role, category, difficulty } = await req.json();
    
    if (!role || !category || !difficulty) {
      return NextResponse.json(
        { error: "role, category, and difficulty are required" },
        { status: 400 }
      );
    }

    const response = await ai.models.generateContent({
      model: "gemini-flash-latest",
      contents: `Generate 5 ${difficulty} ${category} interview questions for a ${role} candidate.`,
      config: {
        responseMimeType: "application/json",
        responseJsonSchema: {
          type: Type.OBJECT,
          properties: {
            questions: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  id: { type: Type.INTEGER },
                  question: { type: Type.STRING },
                  category: { type: Type.STRING },
                },
                propertyOrdering: ["id", "question", "category"],
              },
            },
          },
          propertyOrdering: ["questions"],
        },
      },
    });

    if (response.candidates?.[0]?.finishReason === "SAFETY") {
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
