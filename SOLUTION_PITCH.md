# Krishi Mitra — Kannada Voice Agricultural Advisory

Krishi Mitra is a Kannada-first voice advisory prototype for Karnataka farmers, focused on paddy, arecanut, and coconut. Farmers can describe a crop problem in Kannada or English, receive structured preliminary guidance, and be directed to the Kisan Call Centre at 1800-180-1551 or a local agriculture officer for confirmed diagnosis and product-specific advice.

## The problem

Farmers often need timely, understandable support for crop symptoms, pests, and diseases. Generic search results can be difficult to interpret, may not match the farmer’s crop, and can expose farmers to unsafe or inappropriate chemical recommendations.

Krishi Mitra addresses this with a guided, crop-specific advisory flow and a safety-first approach. It supports paddy, arecanut, and coconut, while limiting unverified or chemical dosage advice.

## What Krishi Mitra does

- Provides a Kannada and English Ask interface for farmer questions.
- Uses Groq-hosted language models to interpret questions and explain relevant guidance.
- Includes a guided voice advisory flow for supported crops.
- Filters advice by crop and directs unsupported crops to appropriate expert referral.
- Avoids unverified chemical dosage recommendations.
- Refers severe, ambiguous, or chemical-use questions to the Kisan Call Centre at 1800-180-1551 and local agriculture/horticulture officers.
- Uses Gnani text-to-speech for browser audio playback.

## Live demo

Live application:
https://krishi-mitra-gn3h.onrender.com/

Open the Ask Krishi Mitra page and try a question such as:

“ನನ್ನ ಭತ್ತದ ಎಲೆಗಳು ಹಳದಿಯಾಗುತ್ತಿವೆ. ಏನು ಮಾಡಬೇಕು?”

Then select Listen to hear the response.

## How it works

1. The farmer enters a question in Kannada or English.
2. The application identifies the request and applies crop and safety rules.
3. Ask Krishi Mitra uses a Groq-hosted language model to interpret the question and generate a structured response.
4. The response can be played through Gnani text-to-speech.
5. For confirmed diagnosis, product selection, or chemical-use decisions, the system directs the farmer to local agricultural expertise and the Kisan Call Centre.

## Safety-first design

Krishi Mitra is designed as preliminary decision support, not a replacement for a qualified agricultural expert.

The system:
- Restricts its supported crop scope to paddy, arecanut, and coconut.
- Does not provide unverified chemical dosage recommendations.
- Directs chemical, severe, or ambiguous cases to expert support.
- Uses referral guidance for the Kisan Call Centre at 1800-180-1551.

## Evidence-backed Solution Hub

We are developing an evidence-based Solution Hub to ground future advice in official agricultural advisories and display source information.

This is currently a local prototype behind a disabled feature flag. It is not enabled in the live submission deployment. Public treatment recommendations remain gated pending agronomic and language review.

## Repository

GitHub repository:
https://github.com/11DDBOY11/Gnani_ai_Competition

## Built for

Gnani AI Great Indian AI Internship Challenge

#GreatIndianAIInternshipChallenge #GnaniAI

