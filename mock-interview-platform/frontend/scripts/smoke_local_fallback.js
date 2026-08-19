// Smoke test for local fallback logic (JavaScript duplication for runtime testing)
function normalizeText(s) {
  if (!s) return '';
  return s.toLowerCase().replace(/[^\n\w\s]/g, ' ').replace(/\s+/g, ' ').trim();
}
function tokenize(s) { return normalizeText(s).split(' ').filter(Boolean); }
function jaccard(a, b) { const sa = new Set(tokenize(a)); const sb = new Set(tokenize(b)); if (sa.size===0 && sb.size===0) return 1; const inter = [...sa].filter(x=>sb.has(x)).length; const union = new Set([...sa,...sb]).size; return union===0?0:inter/union; }

function generateQuestions(role, category, difficulty, num) {
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
    ]
  };
  const pool = templates[category||'default']||templates.default;
  const questions=[];
  for(let i=0;i<num;i++){ const q=pool[i%pool.length]; questions.push({id:`local_${Date.now()}_${i}`,question: role?`${q} (for ${role})`:q,category:category||'general',difficulty:difficulty||'medium',expected_answer:'Expected elements: context, approach, trade-offs, final outcome.'}); }
  return { session_id:`local_questions_${Date.now()}`, questions, fallback:true };
}
function generateModelAnswerFor(question){ const core = normalizeText(question).split(' ').slice(0,10).join(' '); return `A good answer should: summarize the situation, explain the approach and steps taken, mention trade-offs, and conclude with results. Example approach for: ${core}`; }
function analyzeSingleAnswer(question,userAnswer){ const model = generateModelAnswerFor(question||'the question'); const similarity = jaccard(userAnswer||'', model); const simPercent = Math.round(similarity*100); let feedback=''; if(simPercent>70){ feedback='Strong answer — you covered most important points, clear structure, and relevant outcomes.';} else if(simPercent>40){ feedback='Partial: good effort but missing structure or specific outcomes. Try to state the impact and steps more concretely.';} else if(simPercent>15){ feedback='Weak match: the answer diverges from the expected approach. Start with a clear situation + task, then describe actions and results.';} else { feedback='Off-topic or too vague. Focus on concrete steps, measurable impact, and trade-offs.';} return { similarity_score:Number(similarity.toFixed(3)), similarity_percent:simPercent, feedback, model_answer:model } }
function analyzeQAPairs(qaPairs){ const results=(qaPairs||[]).map(p=>{ const question=p.question||p.q||''; const answer=p.answer||p.user_answer||p.response||''; return { question, analysis: analyzeSingleAnswer(question, answer) }; }); const avg = results.length? Math.round(results.reduce((s,r)=> s + (r.analysis.similarity_percent||0),0)/results.length):0; return { overall: { average_similarity_percent: avg }, per_question: results }; }
function analyzeResume(text, roleKeywords=[]){ const t = normalizeText(text||''); const result={sections:{},score:0,notes:[]}; const hasExperience = /experience|work experience|employment/.test(t); const hasEducation = /education|degree|university|college/.test(t); const hasSkills = /skills|technologies|languages|stack/.test(t); result.sections.experience=Boolean(hasExperience); result.sections.education=Boolean(hasEducation); result.sections.skills=Boolean(hasSkills); const yearMatches = Array.from(t.matchAll(/(19|20)\d{2}/g)).map(m=>Number(m[0])); let yearsEst=0; if(yearMatches.length>=2){ yearsEst = Math.max(0, Math.max(...yearMatches)-Math.min(...yearMatches)); } result.estimated_years_experience=yearsEst; const words = new Set(tokenize(t)); let keywordHits=0; for(const k of roleKeywords) if(words.has(k.toLowerCase())) keywordHits++; const keywordMatchPercent = roleKeywords.length? Math.round((keywordHits/roleKeywords.length)*100):0; let score=0; if(hasExperience) score+=30; if(hasSkills) score+=30; if(hasEducation) score+=10; score+=Math.min(yearsEst*2,20); score+=Math.min(keywordMatchPercent/5,10); result.score=Math.min(100,Math.round(score)); result.keyword_match={hits:keywordHits,total:roleKeywords.length,percent:keywordMatchPercent}; if(score<50) result.notes.push('Resume appears sparse. Add more measurable achievements and relevant skills.'); if(yearsEst===0) result.notes.push('No clear years detected; consider adding date ranges for roles.'); return result; }

// Run smoke tests
console.log('--- generateQuestions ---'); console.log(JSON.stringify(generateQuestions('Backend Engineer','technical','medium',3), null, 2));
console.log('\n--- analyzeSingleAnswer ---'); console.log(JSON.stringify(analyzeSingleAnswer('How would you debug a memory leak in production?','I would add logs, trace allocations, run heap analysis and fix issues'), null, 2));
console.log('\n--- analyzeQAPairs ---'); console.log(JSON.stringify(analyzeQAPairs([{question:'Describe a time you led a project', answer:'I led migration and reduced costs'},{question:'How to scale DB', answer:'Use sharding and caching'}]), null, 2));
console.log('\n--- analyzeResume ---'); console.log(JSON.stringify(analyzeResume('John Doe\nExperience: 2018-2023 Company X\nSkills: Python, AWS, SQL', ['python','aws','sql']), null, 2));
