# 🚀 Quick Start - Gemini SDK Migration

Get the new Gemini integration working in 5 minutes.

## 1️⃣ Install Dependencies (1 minute)

```bash
cd frontend
npm install
```

This installs `@google/genai@2.17.0` which is already in `package.json`.

## 2️⃣ Configure Environment (1 minute)

```bash
cp .env.local.example .env.local
```

Edit `.env.local` and add your API key:
```
GEMINI_API_KEY=your-actual-gemini-api-key-here
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_SOCKET_URL=http://localhost:5000
```

Get an API key at [https://aistudio.google.com](https://aistudio.google.com).

## 3️⃣ Start Development Server (1 minute)

```bash
npm run dev
```

Server starts at `http://localhost:3000`.

## 4️⃣ Test the API (1 minute)

### Test Questions Route

```bash
curl -X POST http://localhost:3000/api/interview/questions \
  -H "Content-Type: application/json" \
  -d '{
    "role": "Software Engineer",
    "category": "Technical",
    "difficulty": "Medium"
  }'
```

You should see 5 interview questions in JSON format.

### Test Feedback Route

```bash
curl -X POST http://localhost:3000/api/interview/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "role": "Software Engineer",
    "qaPairs": [
      {"question": "What is REST?", "answer": "REST uses HTTP methods..."},
      {"question": "Explain OOP", "answer": "OOP uses objects and classes..."}
    ]
  }'
```

You should see feedback with scores and suggestions.

## 5️⃣ Use in Your Component (1 minute)

```javascript
import { useInterview } from '@/hooks/useInterview';

export default function MyComponent() {
  const { error, loading, questions, feedback, startInterview, submitForFeedback } = useInterview();
  
  // Start interview
  const handleStart = async () => {
    await startInterview({
      role: 'Software Engineer',
      category: 'Technical',
      difficulty: 'Medium',
    });
    // questions state now contains the 5 questions
  };
  
  // Get feedback
  const handleFeedback = async () => {
    await submitForFeedback('Software Engineer', [
      { question: '...', answer: '...' },
      { question: '...', answer: '...' }
    ]);
    // feedback state now contains the analysis
  };
  
  // Render error if any
  if (error) return <div className="text-red-500">{error}</div>;
  
  // Show loading state
  if (loading) return <div>Generating...</div>;
  
  // Render questions/feedback
  return (
    <div>
      {/* Render your UI here */}
    </div>
  );
}
```

## ✅ Done!

That's it! Your Gemini integration is working.

### What You Just Set Up

✅ **API Routes**: `/api/interview/questions` and `/api/interview/feedback`  
✅ **React Hook**: `useInterview()` for easy state management  
✅ **Error Handling**: User-friendly error messages  
✅ **Loading States**: Built-in loading indicators  
✅ **Schema Validation**: Gemini enforces response structure  

## 📖 Next Steps

- **Full Integration**: See `GEMINI_SDK_IMPLEMENTATION_CHECKLIST.md`
- **Detailed Guide**: See `GEMINI_SDK_MIGRATION_GUIDE.md`
- **Example Component**: See `frontend/src/components/InterviewSessionExample.js`
- **API Reference**: See `GEMINI_SDK_IMPLEMENTATION_SUMMARY.md`

## 🐛 Troubleshooting

### "GEMINI_API_KEY not found"
→ Make sure you created `.env.local` and added your key

### "Cannot find module '@google/genai'"
→ Run `npm install` in the frontend directory

### "Blocked by safety filters"
→ Try a different role/category combination

### API returns 500 error
→ Check that your GEMINI_API_KEY is valid in Google AI Studio

For more help, see the Troubleshooting section in `GEMINI_SDK_MIGRATION_GUIDE.md`.

## 📚 File Reference

| File | Purpose |
|------|---------|
| `frontend/src/app/api/interview/questions/route.ts` | Generate interview questions |
| `frontend/src/app/api/interview/feedback/route.ts` | Generate interview feedback |
| `frontend/src/hooks/useInterview.js` | React hook for interview state |
| `frontend/src/utils/api.js` | API client functions |
| `.env.local.example` | Environment variable template |

## 🎯 Common Tasks

### Customize Question Count
Edit `questions/route.ts` line 18:
```typescript
contents: `Generate 10 ${difficulty}...`  // Change from 5 to 10
```

### Change AI Model
Edit both route.ts files:
```typescript
model: "gemini-2.0-flash",  // Was: gemini-flash-latest
```

### Add Temperature Control
Edit both route.ts files in config:
```typescript
config: {
  temperature: 0.7,  // Higher = more creative (0.0-1.0)
  responseMimeType: "application/json",
  // ...
}
```

### Integrate with Interview Page
Replace your interview page with:
```javascript
import { useInterview } from '@/hooks/useInterview';

export default function InterviewPage() {
  const { questions, feedback, error, loading, startInterview, submitForFeedback } = useInterview();
  // Your implementation here
}
```

---

**Time to Setup**: ~5 minutes  
**Status**: ✅ Ready to Use  
**Next**: Integrate into your interview pages!
