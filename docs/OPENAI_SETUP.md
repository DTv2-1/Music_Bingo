# OpenAI API Setup for Pub Quiz

## Overview
The Pub Quiz feature uses OpenAI GPT-4 to dynamically generate trivia questions based on selected genres.

## Required API Key
You need an OpenAI API key with access to GPT-4.

## Setup Instructions

### 1. Get OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-...`)

### 2. Configure in DigitalOcean
1. Go to your App Platform dashboard
2. Navigate to Settings → App-Level Environment Variables
3. Add new variable:
   - **Key**: `OPENAI_API_KEY`
   - **Value**: `sk-your-actual-key-here`
   - **Scope**: All components
4. Save and redeploy

### 3. Local Development
Add to your `.env` file:
```
OPENAI_API_KEY=sk-your-actual-key-here
```

## How It Works

When generating questions, the system:
1. Calls OpenAI GPT-4 API for each genre
2. Requests specific number of multiple choice OR written questions
3. Receives structured JSON with:
   - Question text
   - Answer options (A/B/C/D for multiple choice)
   - Correct answer
   - Fun facts
   - Difficulty level

## Fallback Behavior
If the API key is missing or the API fails:
- System automatically falls back to hardcoded sample questions
- Quiz will still work, but with limited variety

## Cost Estimate
- GPT-4 costs approximately $0.03 per 1K tokens
- Generating 60 questions (~10 questions × 6 rounds) costs approximately $0.30-0.50
- Budget: ~$15-20/month for typical usage (30-40 quiz sessions)

## Question Types

### Multiple Choice (70% default)
```json
{
  "question": "What is the capital of France?",
  "options": {"A": "Paris", "B": "London", "C": "Berlin", "D": "Madrid"},
  "correct_option": "A",
  "answer": "Paris",
  "difficulty": "easy",
  "fun_fact": "Paris is known as the City of Light"
}
```

### Written Answer (30% default)
```json
{
  "question": "Name a Beatles song",
  "answer": "Various Beatles songs",
  "alternative_answers": ["Hey Jude", "Let It Be", "Yesterday"],
  "difficulty": "easy",
  "fun_fact": "The Beatles have the most number-one hits in history"
}
```

## Customization

In the Host Panel, you can adjust the mix:
- 📝 Multiple Choice (adjustable %)
- ✍️ Written Answer (adjustable %)

The generator will create questions according to these ratios.
