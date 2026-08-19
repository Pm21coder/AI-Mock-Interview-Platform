// Local, server-side fallback for LLM actions when no external LLM is configured.
// This module is intentionally simple and deterministic so the app remains
// functional while a real LLM key is provisioned.

type Params = { [k: string]: any };

function normalizeText(s?: string) {
  if (!s) return '';
  return s
    .toLowerCase()
    .replace(/[^\n\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function tokenize(s: string) {
  return normalizeText(s).split(' ').filter(Boolean);
}

function jaccard(a: string, b: string) {
  const sa = new Set(tokenize(a));
  const sb = new Set(tokenize(b));
  if (sa.size === 0 && sb.size === 0) return 1;
  const inter = [...sa].filter((x) => sb.has(x)).length;
  const union = new Set([...sa, ...sb]).size;
  return union === 0 ? 0 : inter / union;
}

export async function handleLocalFallback(action: string | undefined, prompt: string | undefined, params: Params) {
  const act = (action || '').toLowerCase();

  // Simple question templates
  function generateQuestions(role: string | undefined, category: string | undefined, difficulty: string | undefined, num: number) {
    const templates = {
      technical: [
        'Explain a time you diagnosed a production issue and how you fixed it.',
        'How would you design a scalable caching layer for a read-heavy service?',
        'Describe how you would debug a memory leak in a long-running service.'
      ],
      behavioral: [
        'Tell me about a time you faced conflict in a team. How did you handle it?',
        'Describe a project you led and what the outcome was.',
        'How do you prioritize work when everything is urgent?'
      ],
      system_design: [
        'Design a URL shortening service. Explain storage, scale, and bottlenecks.',
        'Design a notification service for mobile and email delivery.',
        'How would you design a high-throughput event ingestion pipeline?'
      ],
      default: [
        'Tell me about a challenging problem you solved recently.',
        'Walk me through your most impactful project.'
      ],
    } as Record<string, string[]>;

    const pool = templates[category || 'default'] || templates.default;
    const questions = [] as any[];
    for (let i = 0; i < num; i++) {
      const q = pool[i % pool.length];
      questions.push({
        id: `local_${Date.now()}_${i}`,
        question: role ? `${q} (for ${role})` : q,
        category: category || 'general',
        difficulty: difficulty || 'medium',
        expected_answer: 'Expected elements: context, approach, trade-offs, final outcome.',
      });
    }
    return { session_id: `local_questions_${Date.now()}`, questions, fallback: true };
  }

  function generateModelAnswerFor(question: string) {
    // Create a short template answer focused on structure and keywords
    const core = normalizeText(question).split(' ').slice(0, 10).join(' ');
    return `A good answer should: summarize the situation, explain the approach and steps taken, mention trade-offs, and conclude with results. Example approach for: ${core}`;
  }

  function analyzeSingleAnswer(question: string, userAnswer: string) {
    const model = generateModelAnswerFor(question || prompt || 'the question');
    const similarity = jaccard(userAnswer || '', model);
    const simPercent = Math.round(similarity * 100);
    let feedback = '';
    if (simPercent > 70) {
      feedback = 'Strong answer — you covered most important points, clear structure, and relevant outcomes.';
    } else if (simPercent > 40) {
      feedback = 'Partial: good effort but missing structure or specific outcomes. Try to state the impact and steps more concretely.';
    } else if (simPercent > 15) {
      feedback = 'Weak match: the answer diverges from the expected approach. Start with a clear situation + task, then describe actions and results.';
    } else {
      feedback = 'Off-topic or too vague. Focus on concrete steps, measurable impact, and trade-offs.';
    }

    return {
      similarity_score: Number((similarity).toFixed(3)),
      similarity_percent: simPercent,
      feedback,
      model_answer: model,
    };
  }

  function analyzeQAPairs(qaPairs: any[]) {
    const results = (qaPairs || []).map((p: any) => {
      const question = p.question || p.q || prompt || '';
      const answer = p.answer || p.user_answer || p.response || '';
      return {
        question,
        analysis: analyzeSingleAnswer(question, answer),
      };
    });
    const avg = results.length ? Math.round(results.reduce((s: number, r: any) => s + (r.analysis.similarity_percent || 0), 0) / results.length) : 0;
    return { overall: { average_similarity_percent: avg }, per_question: results };
  }

  function analyzeResume(text: string, roleKeywords: string[] = []) {
    const t = normalizeText(text || '');
    const result: any = { sections: {}, score: 0, notes: [] };
    // Detect sections
    const hasExperience = /experience|work experience|employment/.test(t);
    const hasEducation = /education|degree|university|college/.test(t);
    const hasSkills = /skills|technologies|languages|stack/.test(t);
    result.sections.experience = Boolean(hasExperience);
    result.sections.education = Boolean(hasEducation);
    result.sections.skills = Boolean(hasSkills);

    // Estimate years of experience by looking for year ranges like 2018-2021 or 'since 2019'
    const yearMatches = Array.from(t.matchAll(/(19|20)\d{2}/g)).map((m) => Number(m[0]));
    let yearsEst = 0;
    if (yearMatches.length >= 2) {
      const minY = Math.min(...yearMatches);
      const maxY = Math.max(...yearMatches);
      yearsEst = Math.max(0, maxY - minY);
    }
    result.estimated_years_experience = yearsEst;

    // Keyword match
    const words = new Set(tokenize(t));
    let keywordHits = 0;
    for (const k of roleKeywords) if (words.has(k.toLowerCase())) keywordHits++;
    const keywordMatchPercent = roleKeywords.length ? Math.round((keywordHits / roleKeywords.length) * 100) : 0;

    // Score: simple weighted formula
    let score = 0;
    if (hasExperience) score += 30;
    if (hasSkills) score += 30;
    if (hasEducation) score += 10;
    score += Math.min(yearsEst * 2, 20); // up to 20
    score += Math.min(keywordMatchPercent / 5, 10); // up to 10
    result.score = Math.min(100, Math.round(score));

    result.keyword_match = { hits: keywordHits, total: roleKeywords.length, percent: keywordMatchPercent };
    if (score < 50) result.notes.push('Resume appears sparse. Add more measurable achievements and relevant skills.');
    if (yearsEst === 0) result.notes.push('No clear years detected; consider adding date ranges for roles.');
    return result;
  }

  // Action routing
  if (act === 'generate_questions') {
    const role = params?.role || params?.job || undefined;
    const category = params?.category || params?.topic || 'technical';
    const difficulty = params?.difficulty || 'medium';
    const num = Number(params?.num_questions || params?.num || 3) || 3;
    return { ok: true, provider: 'local-fallback', result: generateQuestions(role, category, difficulty, num), raw: {} };
  }

  if (act === 'analyze_answer' || act === 'analyze_qa_pairs') {
    // If analyze_qa_pairs send array, otherwise single QA
    if (Array.isArray(params?.qaPairs) || Array.isArray(params?.qa_pairs) || Array.isArray(params?.qa)) {
      const qa = params?.qaPairs || params?.qa_pairs || params?.qa || [];
      return { ok: true, provider: 'local-fallback', result: analyzeQAPairs(qa), raw: {} };
    }
    // single answer analysis
    const question = params?.question || params?.q || prompt || '';
    const answer = params?.answer || params?.transcript || params?.text || '';
    return { ok: true, provider: 'local-fallback', result: analyzeSingleAnswer(question, answer), raw: {} };
  }

  if (act === 'resume_analysis' || act === 'analyze_resume' || act === 'resume') {
    const text = params?.resume_text || params?.resume || params?.cv || prompt || '';
    const roleKeywords = (params?.role_keywords || params?.keywords || []).map((x: any) => String(x));
    return { ok: true, provider: 'local-fallback', result: analyzeResume(text, roleKeywords), raw: {} };
  }

  // Default: echo prompt as a safe short guidance
  return { ok: true, provider: 'local-fallback', result: { text: prompt || 'No prompt' }, raw: {} };
}
