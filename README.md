# Gemini Assistant — Alexa custom skill (import-ready)

Ask Google Gemini anything by voice. Import this repository into the
Alexa developer console (**Import skill**, paste the repository URL),
then set the Lambda environment variables and deploy.

- Invocation name: **gemini assistant**
- Locales: **en-US** and **ar-SA** (answers in the language you ask in)
- Backend: Python, standard library only (`lambda/py/lambda_function.py`,
  handler `lambda_function.lambda_handler`)
- Answers are capped at ~3 short sentences for voice, plain text only.

## After import

1. In the Alexa-hosted skill, set the Lambda environment variables:
   - `GEMINI_API_KEY` = your key from Google AI Studio
     (https://aistudio.google.com/ → Get API key; free tier available)
   - `GEMINI_MODEL` = `gemini-2.5-flash`
2. Deploy the skill.
3. Test in the simulator:
   - "Alexa, ask gemini assistant what is the capital of France"
   - "Alexa, ask gemini assistant عاصمة فرنسا ايه"

## Security

No secrets are committed in this repository. The Gemini API key is
never in the code — it goes into the Lambda environment variables only.
This is Gemini answering, not Muse: no memory, no files, no access to
other apps. Test mode only; no certification needed for personal use.
