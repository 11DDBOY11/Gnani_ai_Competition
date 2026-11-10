import asyncio
import json
import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

import sys
sys.path.insert(0, ".")
from app.agri_search import generate_agri_answer

TRANSLATE_QUESTION_SYSTEM = """You are a strict, literal agricultural query translator from Kannada to English.
Translate the farmer's question faithfully into English.

Rules:
1. Preserve the exact crop name (e.g., ಭತ್ತ = Paddy/Rice, ಅಡಿಕೆ = Arecanut/Betelnut, ತೆಂಗು = Coconut), plant part, symptoms, negations (e.g., "no insects seen"), durations, and quantities.
2. Do NOT diagnose the crop or problem.
3. Do NOT add missing context, assumed crops, or background info.
4. Do NOT answer the question.
5. If a specific Kannada term is unclear, retain the original word in quotes and flag ambiguity.
Return JSON only: {"english_translation": "...", "detected_crop": "... or null", "has_negation": boolean, "is_ambiguous": boolean}
"""

TRANSLATE_ANSWER_SYSTEM = """You are a careful agricultural translator from English to simple Kannada for farmers in Karnataka.
Translate the English advisory answer into simple, natural, clear Kannada.

Rules:
1. Preserve uncertainty: phrases like "possible cause", "might be", "consider" must NOT become confirmed diagnoses.
2. Preserve all cautions, safety restrictions, and expert referrals (e.g., Kisan Call Centre 1800-180-1551 or local agriculture officer) completely intact.
3. Preserve negations, numbers, and units exactly.
4. Do NOT add chemical treatments, brand names, or dosages not present in the English text.
5. Do NOT remove warnings.
6. Use simple, easily understood Kannada.
Return JSON only: {"kannada_translation": "..."}
"""

async def call_groq_json(system_prompt: str, user_prompt: str) -> dict:
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {"type": "json_object"},
        "max_completion_tokens": 1500,
        "temperature": 0.1,
    }
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
                resp = await client.post(GROQ_CHAT_URL, headers=headers, json=payload)
                if resp.status_code == 429:
                    print(f"  [429 Rate Limit encountered. Sleeping 5s before retry {attempt+1}...]")
                    await asyncio.sleep(5.0)
                    continue
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            if attempt == 2:
                raise e
            await asyncio.sleep(3.0)

async def translate_kannada_to_english(kn_question: str) -> dict:
    return await call_groq_json(TRANSLATE_QUESTION_SYSTEM, f"Kannada question to translate: {kn_question}")

async def translate_english_to_kannada(en_answer: str) -> str:
    res = await call_groq_json(TRANSLATE_ANSWER_SYSTEM, f"English answer to translate to Kannada: {en_answer}")
    return res.get("kannada_translation", "").strip()

async def run_pipeline(kn_question: str, crop=None, district=None):
    # Baseline: Current direct Kannada path
    t_base_start = time.time()
    direct_kn_res = await generate_agri_answer(kn_question, language="kn", crop=crop, district=district)
    t_base = time.time() - t_base_start
    await asyncio.sleep(2.0)
    
    # Experimental 3-stage bridge
    t_exp_start = time.time()
    
    # Stage 1: Kannada -> English
    t1_s = time.time()
    q_trans = await translate_kannada_to_english(kn_question)
    en_q = q_trans.get("english_translation", "")
    t1 = time.time() - t1_s
    await asyncio.sleep(2.0)
    
    # Stage 2: English Answer via existing agri_search
    t2_s = time.time()
    en_res = await generate_agri_answer(en_q, language="en", crop=crop, district=district)
    en_ans = en_res["answer"]
    t2 = time.time() - t2_s
    await asyncio.sleep(2.0)
    
    # Stage 3: English Answer -> Kannada
    t3_s = time.time()
    final_kn_ans = await translate_english_to_kannada(en_ans)
    t3 = time.time() - t3_s
    
    t_exp = time.time() - t_exp_start
    
    return {
        "question_kn": kn_question,
        "baseline_direct": {
            "answer": direct_kn_res["answer"],
            "confidence": direct_kn_res["confidence"],
            "needs_review": direct_kn_res["needs_expert_review"],
            "latency": t_base
        },
        "experimental_bridge": {
            "stage1_translated_q": en_q,
            "stage1_meta": q_trans,
            "stage1_latency": t1,
            "stage2_english_ans": en_ans,
            "stage2_confidence": en_res["confidence"],
            "stage2_needs_review": en_res["needs_expert_review"],
            "stage2_latency": t2,
            "stage3_final_kn": final_kn_ans,
            "stage3_latency": t3,
            "total_latency": t_exp
        }
    }

TEST_QUESTIONS = [
    ("1. Paddy leaves turning yellow", "ನನ್ನ ಭತ್ತದ ಎಲೆಗಳು ಹಳದಿಯಾಗುತ್ತಿವೆ. ಏನು ಮಾಡಬೇಕು?"),
    ("2. Arecanut fruits falling", "ಅಡಿಕೆ ಕಾಯಿಗಳು ಉದುರುತ್ತಿವೆ, ಪರಿಹಾರ ತಿಳಿಸಿ"),
    ("3. Spots on coconut leaves", "ತೆಂಗಿನ ಎಲೆಗಳ ಮೇಲೆ ಕಂದು ಚುಕ್ಕೆಗಳಿವೆ"),
    ("4. Negation question", "ಭತ್ತದಲ್ಲಿ ಯಾವುದೇ ಹುಳುಗಳು ಕಂಡಿಲ್ಲ, ಆದರೆ ಎಲೆಗಳು ಒಣಗುತ್ತಿವೆ"),
    ("5. Ambiguous question (clarification really needed)", "ಗಿಡದಲ್ಲಿ ರೋಗ ಬಂದಿದೆ, ಏನು ಮಾಡಬೇಕು?"),
    ("6. Pesticide dosage request (safety gate check)", "ಭತ್ತದ ಬೆಂಕಿ ರೋಗಕ್ಕೆ ಎಷ್ಟು ಪ್ರಮಾಣದ ಔಷಧ ಸಿಂಪಡಿಸಬೇಕು?")
]

async def main():
    print("="*80)
    print("RUNNING ISOLATED KANNADA -> ENGLISH -> ANSWER -> KANNADA EXPERIMENT")
    print("="*80)
    
    results = []
    for label, q in TEST_QUESTIONS:
        print(f"\n>>> Evaluating: {label}")
        print(f"    Kannada Input: {q}")
        res = await run_pipeline(q)
        results.append((label, res))
        
        print("\n    [BASELINE (Direct Kannada)]")
        print(f"    Latency: {res['baseline_direct']['latency']:.2f}s")
        print(f"    Answer: {res['baseline_direct']['answer'][:200]}...")
        
        print("\n    [EXPERIMENTAL BRIDGE (3-Stage)]")
        print(f"    Stage 1 (KN -> EN Q): {res['experimental_bridge']['stage1_translated_q']} ({res['experimental_bridge']['stage1_latency']:.2f}s)")
        print(f"    Stage 2 (EN Ans):     {res['experimental_bridge']['stage2_english_ans'][:200]}... ({res['experimental_bridge']['stage2_latency']:.2f}s)")
        print(f"    Stage 3 (EN -> KN Ans): {res['experimental_bridge']['stage3_final_kn'][:200]}... ({res['experimental_bridge']['stage3_latency']:.2f}s)")
        print(f"    Total Bridge Latency (excl sleep): {res['experimental_bridge']['total_latency'] - 4.0:.2f}s")
        print("=" * 80)
        await asyncio.sleep(3.0)
        
    with open("submission/experiment_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nSaved detailed results to submission/experiment_results.json")

if __name__ == "__main__":
    asyncio.run(main())
