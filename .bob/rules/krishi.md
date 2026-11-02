Project: Krishi Mitra, Kannada voice advisory on Gnani Prisma v3.0 STT and Timbre TTS.
Hard rules:
1. Never invent pesticide names, doses or Kannada agronomy facts. Chemical advice stays blocked unless chemical.reviewed is true and all CHEM_FIELDS are filled (chemical_allowed() in app/dialogue.py). Never weaken this gate.
2. Never add Kannada keywords or dialect synonyms you cannot justify. Mark any new Kannada text "NEEDS NATIVE REVIEW".
3. No new dependencies unless I approve. No Docker, Prometheus, JSON logging or SMS gateway work before Nov 10.
4. Never log or print GNANI_API_KEY or full phone numbers.
5. One task at a time. Run `pytest -q` after every change and show me the output. Do not modify existing tests to make them pass.
6. Do not claim anything works unless a command you ran proves it.