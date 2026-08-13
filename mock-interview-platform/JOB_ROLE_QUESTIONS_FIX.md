# Job-Role-Specific Questions Fix

## Problem

Interview questions were not role-specific because:

1. Old Gemini models (gemini-2.5-flash) were no longer available
2. When the API call failed, the fallback only supported 2 job roles (software_engineer, data_scientist)
3. All other job roles would fall back to generic software engineer questions

## Solution

### 1. Updated Gemini Model Fallback Chain

**File**: `backend/app/services/gemini_service.py`

- Changed from: gemini-2.5-flash → gemini-2.5-pro → gemini-3.5-flash → gemini-3.6-flash
- Changed to: gemini-3.1-flash-lite → gemini-3.5-flash → gemini-3.6-flash → gemini-flash-latest
- Prioritizes lighter models with better free-tier quota availability

### 2. Updated Default Model in Config

**File**: `backend/.env`

- Changed from: `GOOGLE_GEMINI_MODEL=gemini-2.5-flash`
- Changed to: `GOOGLE_GEMINI_MODEL=gemini-3.1-flash-lite`
- Lighter model with better API quota for free tier users

### 3. Enhanced Fallback Questions System

**File**: `backend/app/services/gemini_service.py`

#### Added Support for More Job Roles

- software_engineer (3 categories: technical, behavioral, general)
- data_scientist (3 categories)
- product_manager (3 categories)
- devops_engineer (3 categories)

#### Improved Fallback Logic

- No longer defaults to software_engineer questions for unknown roles
- Generates dynamic, job-role-specific questions for ANY role not in the hardcoded list
- Example for a "UX Designer" role that's not in the database:

```python
"What is your experience with the key technologies and skills required for a UX Designer position?"
"Describe a challenging behavioral problem you solved as a UX Designer."
"How do you stay current with industry trends and best practices relevant to UX Designer?"
"Tell me about how you would measure success in a UX Designer role."
```

## How It Works Now

### Scenario 1: User selects "Product Manager"

✅ API is available → Gemini generates custom Product Manager questions using the new models
✅ API quota exceeded → Fallback uses the new Product Manager questions (now included in fallback pool)

### Scenario 2: User selects "Backend Engineer" (not in hardcoded list)

✅ API is available → Gemini generates Backend Engineer-specific questions  
✅ API quota exceeded → Fallback generates dynamic role-specific questions that mention "Backend Engineer"

### Scenario 3: User selects a very custom role like "Machine Learning Ops Engineer"

✅ API is available → Gemini creates questions tailored to this specific role
✅ API quota exceeded → Fallback creates questions that reference the actual job role specified

## Testing

Run the integration test to verify:

```bash
cd backend
python test_gemini_integration.py
```

You should see:

- ✅ Configuration check passes
- ✅ Service available: True
- ✅ Questions are generated (either via API or fallback)
- ✅ Answer analysis works
- ✅ Resume analysis works

## Benefits

1. **Job-Role-Specific Questions**: Now generates relevant questions for ANY job role, not just software engineers
2. **Better Free-Tier Quotas**: Using lighter models (gemini-3.1-flash-lite) reduces quota usage
3. **Graceful Degradation**: Even when API fails, users get job-role-specific fallback questions
4. **Easy to Expand**: Adding new job roles to fallback pool is simple
5. **Customizable**: When users enter custom roles, questions mention those roles specifically

## Files Changed

- `backend/app/services/gemini_service.py` - Updated model list and fallback questions
- `backend/.env` - Updated default model to gemini-3.1-flash-lite
