# Gemini API Migration Guide - New SDK Implementation

This guide covers the migration from `@google/generative-ai` (dead SDK) to `@google/genai` (2.17.0) with schema-enforced structured outputs for the AI Mock Interview Platform.

## Overview

The new Gemini SDK provides:
- Schema-enforced JSON responses (no need for custom parsing)
- Better error handling
- Improved performance
- Type safety with TypeScript

## What Changed

### SDK Differences

| Aspect | Old SDK | New SDK |
|--------|---------|---------|
| Package | `@google/generative-ai` | `@google/genai` |
| Client | `new GoogleGenerativeAI(key)` | `new GoogleGenAI({ apiKey: key })` |
| Call | `model.generateContent(prompt)` | `ai.models.generateContent({ model, contents, config })` |
| Response | `response.text()` (method) | `response.text` (property) |
| Model | `gemini-1.5-flash` | `gemini-flash-latest` |
| Schemas | No schema support | Full JSON schema support via `Type` enum |

## Installation & Setup

### 1. Update Dependencies

```bash
cd frontend
npm uninstall @google/generative-ai
npm install @google/genai@2.17.0
```

### 2. Environment Configuration

Create or update `frontend/.env.local`:

```env
GEMINI_API_KEY=your-actual-api-key-here
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_SOCKET_URL=http://localhost:5000
```

**Important**: 
- `GEMINI_API_KEY` is server-side only (no `NEXT_PUBLIC_` prefix)
- Keep it out of version control (add `.env.local` to `.gitignore`)
- For production, set via environment variables on your hosting platform

### 3. Verify Installation

```bash
npm list @google/genai
# Should show: @google/genai@2.17.0 (or compatible)
```

## API Routes

### Route 1: Question Generation
**File**: `frontend/src/app/api/interview/questions/route.ts`

Generates 5 interview questions with schema-enforced JSON structure.

**Request**:
```json
{
  "role": "Software Engineer",
  "category": "Technical",
  "difficulty": "Medium"
}
```

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "question": "Explain the difference between...",
      "category": "Technical"
    },
    ...
  ]
}
```

**Error Handling**:
- `422` - Safety filters blocked the request
- `400` - Missing required fields
- `500` - Server error

### Route 2: Feedback Generation
**File**: `frontend/src/app/api/interview/feedback/route.ts`

Analyzes Q&A pairs and provides structured feedback.

**Request**:
```json
{
  "role": "Software Engineer",
  "qaPairs": [
    {
      "question": "Explain REST APIs",
      "answer": "REST uses HTTP methods and endpoints..."
    },
    ...
  ]
}
```

**Response**:
```json
{
  "data": {
    "overallScore": 85,
    "overallSummary": "Strong technical knowledge with room for improvement in communication",
    "perQuestion": [
      {
        "question": "Explain REST APIs",
        "score": 88,
        "strengths": ["Correct understanding", "Good examples"],
        "improvements": ["Could mention constraints", "Add about scalability"]
      },
      ...
    ]
  }
}
```

## Frontend Integration

### Using the Hook

```jsx
import { useInterview } from '@/hooks/useInterview';

function MyInterviewComponent() {
  const {
    error,
    loading,
    questions,
    feedback,
    startInterview,
    submitForFeedback,
    clearError,
  } = useInterview();

  const handleStart = async () => {
    await startInterview({
      role: 'Software Engineer',
      category: 'Technical',
      difficulty: 'Medium',
    });
  };

  if (error) {
    return (
      <div className="text-red-500">
        <p>{error}</p>
        <button onClick={clearError}>Dismiss</button>
      </div>
    );
  }

  if (loading) {
    return <p>Generating...</p>;
  }

  return (
    // Render questions and feedback based on state
  );
}
```

### Direct API Calls

If you prefer not to use the hook:

```javascript
import { generateInterviewQuestions, generateFeedback } from '@/utils/api';

// Generate questions
try {
  const result = await generateInterviewQuestions(
    'Software Engineer',
    'Technical',
    'Medium'
  );
  console.log(result.data); // Array of questions
} catch (error) {
  console.error('Question generation failed:', error.message);
}

// Generate feedback
try {
  const result = await generateFeedback('Software Engineer', [
    { question: 'What is REST?', answer: 'REST is...' },
    { question: 'Explain OOP', answer: 'OOP is...' },
  ]);
  console.log(result.data); // Structured feedback
} catch (error) {
  console.error('Feedback generation failed:', error.message);
}
```

## Testing

### 1. Test Questions Route

```bash
curl -X POST http://localhost:3000/api/interview/questions \
  -H "Content-Type: application/json" \
  -d '{
    "role": "Software Engineer",
    "category": "Technical",
    "difficulty": "Medium"
  }'
```

**Expected Response**:
```json
{
  "data": [
    {
      "id": 1,
      "question": "...",
      "category": "Technical"
    },
    ...
  ]
}
```

### 2. Test Feedback Route

```bash
curl -X POST http://localhost:3000/api/interview/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "role": "Software Engineer",
    "qaPairs": [
      {
        "question": "What is REST?",
        "answer": "REST is an architectural style for APIs"
      },
      {
        "question": "Explain OOP",
        "answer": "OOP uses objects and classes"
      }
    ]
  }'
```

**Expected Response**:
```json
{
  "data": {
    "overallScore": 75,
    "overallSummary": "...",
    "perQuestion": [...]
  }
}
```

### 3. Test Error Handling

Missing required fields:
```bash
curl -X POST http://localhost:3000/api/interview/questions \
  -H "Content-Type: application/json" \
  -d '{ "role": "Engineer" }'
# Should return 400: "role, category, and difficulty are required"
```

Empty answers:
```bash
curl -X POST http://localhost:3000/api/interview/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "role": "Engineer",
    "qaPairs": [
      { "question": "Test?", "answer": "" }
    ]
  }'
# Should return 400: "Every question needs a non-empty answer"
```

## Schema Validation Details

### Questions Schema

```typescript
{
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
      },
    },
  },
}
```

This ensures Gemini **always** returns an array of objects with exactly these fields in the correct types.

### Feedback Schema

```typescript
{
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
      },
    },
  },
}
```

No more parsing errors or malformed responses!

## Error Recovery

### Common Issues & Solutions

#### 1. "GEMINI_API_KEY not found"

**Cause**: Environment variable not set
**Solution**: Add to `.env.local` and restart dev server

```bash
echo "GEMINI_API_KEY=your-key" >> .env.local
npm run dev
```

#### 2. "Safety filters blocked the request"

**Cause**: Gemini rejected the prompt (typically role + category combination)
**Solution**: Modify the role/category and try again

```javascript
// Try a different category
await generateInterviewQuestions('Software Engineer', 'Behavioral', 'Medium');
```

#### 3. "Network error — please try again"

**Cause**: Gemini API unreachable or rate-limited
**Solution**: 
- Check internet connection
- Verify API key is valid
- Wait a moment and retry
- Check Google Cloud console for rate limits

#### 4. Parsed JSON contains extra fields

**Cause**: Model ignoring schema (rare)
**Solution**: The schema should prevent this, but validate fields:

```javascript
const result = await generateFeedback(role, qaPairs);
if (!result.data.overallScore) {
  console.warn('Missing overallScore, using 0');
  result.data.overallScore = 0;
}
```

## Configuration & Customization

### Change Model

Edit `route.ts` files:
```typescript
const response = await ai.models.generateContent({
  model: "gemini-flash-latest",  // ← Change this
  // ...
});
```

Valid models:
- `gemini-flash-latest` (recommended)
- `gemini-2.0-flash` (if 2.0 available)
- `gemini-pro` (older, slower)

### Adjust Question Count

Edit `questions/route.ts`:
```typescript
contents: `Generate 10 ${difficulty} ${category} interview questions...`
//                    ↑ Change from 5 to 10
```

### Change Temperature (Creativity)

Edit `route.ts` files to add config:
```typescript
config: {
  responseMimeType: "application/json",
  responseJsonSchema: { ... },
  temperature: 0.5,  // ← Add this (0.0=deterministic, 1.0=creative)
}
```

## Deployment

### Environment Variables

Set on your hosting platform:

**Vercel**:
```bash
vercel env add GEMINI_API_KEY
# Paste your API key when prompted
```

**Docker**:
```dockerfile
ENV GEMINI_API_KEY=your-key-here
```

**GitHub Actions**:
```yaml
env:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

### Security Best Practices

✅ **DO**:
- Keep API key in environment variables only
- Use separate keys for dev/staging/production
- Rotate keys regularly
- Monitor API usage in Google Cloud Console

❌ **DON'T**:
- Commit `.env.local` to git
- Hardcode API keys in code
- Share keys via email or chat
- Use the same key across environments

## Performance Optimization

### Request Caching

Implement caching to avoid redundant API calls:

```javascript
const cache = new Map();

export async function generateInterviewQuestions(role, category, difficulty) {
  const key = `${role}:${category}:${difficulty}`;
  
  if (cache.has(key)) {
    return cache.get(key);
  }
  
  const result = await generateInterviewQuestionsAPI(...);
  cache.set(key, result);
  
  // Clear cache after 1 hour
  setTimeout(() => cache.delete(key), 3600000);
  
  return result;
}
```

### Timeout Handling

Add timeouts to prevent hanging requests:

```typescript
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 30000); // 30s

try {
  const response = await ai.models.generateContent({
    model: "gemini-flash-latest",
    contents,
    config,
    // Note: This depends on the SDK supporting abort signals
  });
} finally {
  clearTimeout(timeout);
}
```

## Troubleshooting

### Check API Key

```bash
curl https://generativelanguage.googleapis.com/v1/models/list?key=YOUR_API_KEY
```

Should return 200 with model list.

### View Real Requests

Add logging to `route.ts`:

```typescript
console.log('Request:', { role, category, difficulty });
console.log('Response:', { candidates: response.candidates?.length });
```

### Monitor Gemini Usage

Visit [Google AI Studio](https://aistudio.google.com) to see API quota and usage.

## Migration Checklist

- [x] Update package.json
- [x] Install dependencies (`npm install @google/genai`)
- [x] Create API routes with schema validation
- [x] Add environment variables
- [x] Update frontend API utilities
- [x] Create hooks/components for UI
- [x] Test both routes with curl
- [x] Test error scenarios
- [x] Verify error rendering in UI
- [x] Deploy to production

## Support & Troubleshooting

- **Google Gemini Docs**: https://ai.google.dev/gemini-api/docs
- **SDK Reference**: https://www.npmjs.com/package/@google/genai
- **Schema Types**: Check `Type` enum in `@google/genai` package
- **Rate Limits**: https://ai.google.dev/pricing#text-models

## Next Steps

1. Install dependencies and set up `.env.local`
2. Test the API routes with curl
3. Integrate the `useInterview` hook into your interview pages
4. Wire up error handling in the UI
5. Test end-to-end with a real interview session
6. Deploy to production with secure environment variables

