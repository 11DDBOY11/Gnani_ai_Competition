import json, pathlib, re, unicodedata
from dataclasses import dataclass, field

KB_PATH = pathlib.Path(__file__).with_name("kb.json")
KB = {a["id"]: a for a in json.loads(KB_PATH.read_text(encoding="utf-8"))["advisories"]}

CROPS = {
    "paddy": ["ಭತ್ತ", "ಬತ್ತ", "ಅಕ್ಕಿ", "ಗದ್ದೆ", "paddy", "rice", "bhatta"],
    "arecanut": ["ಅಡಿಕೆ", "ಅಡಕೆ", "ಸುಪಾರಿ", "arecanut", "areca", "adike"],
    "coconut": ["ತೆಂಗು", "ತೆಂಗಿನ", "ನಾರಿಕೇಳ", "coconut", "thengu"],
}
CROP_KN = {"paddy": "ಭತ್ತ", "arecanut": "ಅಡಿಕೆ", "coconut": "ತೆಂಗು"}

PROBLEMS = {
    "paddy_leaf_folder": ["ಎಲೆ ಸುತ್ತ", "ಎಲೆ ಮಡಚ", "ಸುತ್ತಿಕೊಂಡ", "ಸುತ್ತಿಕೊಳ್ಳ", "leaf folder", "leaf roll", "leaf fold"],
    "paddy_blast": ["ಬೆಂಕಿ ರೋಗ", "ಬೆಂಕಿರೋಗ", "ಕಣ್ಣಿನ ಆಕಾರ", "ಕಂದು ಚುಕ್ಕೆ", "blast"],
    "arecanut_koleroga": ["ಕಾಯಿ ಕೊಳೆ", "ಕೊಳೆ ರೋಗ", "ಕೊಳೆರೋಗ", "ಮಹಾಲಿ", "ಕೊಳೆತ", "ಕೊಳೆ", "koleroga", "fruit rot"],
    "coconut_rhino_beetle": ["ಕೊಂಬಿನ ದುಂಬಿ", "ದುಂಬಿ", "beetle"],
    "coconut_bud_rot": ["ಸುಳಿ ಕೊಳೆ", "ಸುಳಿ", "bud rot"],
}

STAGES = {
    "seedling": ["ಸಸಿ", "ಚಿಕ್ಕ", "ಸಣ್ಣ", "ನಾಟಿ", "seedling", "small"],
    "flowering": ["ಹೂ", "ಹೊರಬ", "flower"],
    "grain": ["ಕಾಳು", "ತೆನೆ", "ಕಾಯಿ ಕಟ್ಟ", "ಕಟಾವು", "grain"],
}

GOODBYE = ["ಧನ್ಯವಾದ", "ಸಾಕು", "ಇಷ್ಟೇ", "thank", "bye"]
REPEAT = ["ಮತ್ತೆ ಹೇಳಿ", "ಇನ್ನೊಮ್ಮೆ", "ಪುನಃ", "repeat"]

T = {
    "greeting": ["ನಮಸ್ಕಾರ. ಇದು ಕೃಷಿ ಮಿತ್ರ ಸೇವೆ.", "ಸೇವೆ ಸುಧಾರಿಸಲು ಈ ಕರೆಯನ್ನು ದಾಖಲಿಸಲಾಗುತ್ತದೆ.", "ನಿಮ್ಮ ಬೆಳೆ ಮತ್ತು ಸಮಸ್ಯೆಯನ್ನು ಕನ್ನಡದಲ್ಲಿ ಹೇಳಿ."],
    "ask_crop": ["ನಿಮ್ಮ ಬೆಳೆ ಯಾವುದು? ಭತ್ತ, ಅಡಿಕೆ, ಅಥವಾ ತೆಂಗು?"],
    "ask_problem": ["ಬೆಳೆಯಲ್ಲಿ ಏನು ಸಮಸ್ಯೆ ಕಾಣುತ್ತಿದೆ? ಎಲೆ, ಕಾಯಿ, ಅಥವಾ ಗಿಡದ ಬಗ್ಗೆ ಹೇಳಿ."],
    "ask_stage": ["ಬೆಳೆ ಯಾವ ಹಂತದಲ್ಲಿದೆ? ಸಸಿ, ಹೂ ಬಿಡುವ ಹಂತ, ಅಥವಾ ಕಾಳು ಕಟ್ಟುವ ಹಂತ?"],
    "reprompt": ["ಕ್ಷಮಿಸಿ, ಸರಿಯಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಹೇಳಿ."],
    "escalate": ["ಈ ಬಗ್ಗೆ ನಿಖರವಾದ ಸಲಹೆ ನೀಡಲು ನನಗೆ ಸಾಧ್ಯವಿಲ್ಲ.", "ದಯವಿಟ್ಟು ಹತ್ತಿರದ ಕೃಷಿ ಅಧಿಕಾರಿ ಅಥವಾ ರೈತ ಸಂಪರ್ಕ ಕೇಂದ್ರವನ್ನು ಸಂಪರ್ಕಿಸಿ."],
    "no_chem": ["ಔಷಧದ ಹೆಸರು ಮತ್ತು ಪ್ರಮಾಣಕ್ಕಾಗಿ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ."],
    "safety": ["ಸಿಂಪಡಿಸುವಾಗ ಕೈಗವಸು ಮತ್ತು ಮುಖಕ್ಕೆ ಮಾಸ್ಕ್ ಧರಿಸಿ. ಲೇಬಲ್ ಓದಿ."],
    "bye": ["ಧನ್ಯವಾದಗಳು. ಮತ್ತೆ ಬೇಕಾದರೆ ಕರೆ ಮಾಡಿ."],
}

CHEM_FIELDS = ["product", "dose", "water", "preharvest_days", "source", "reviewed_by", "review_date"]


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").replace("\u200c", "").replace("\u200d", "")
    s = re.sub(r"[.,!?;:'()\"-]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def _best(text, table, only=None):
    best, score = None, 0
    for key, kws in table.items():
        if only and key not in only:
            continue
        sc = sum(len(normalize(k)) for k in kws if normalize(k) in text)
        if sc > score:
            best, score = key, sc
    return best


def find_crop(text):
    return _best(normalize(text), CROPS)


def find_problem(text, crop=None):
    t = normalize(text)
    if crop:
        only = [k for k in PROBLEMS if KB[k]["crop"] == crop]
        hit = _best(t, PROBLEMS, only)
        if hit:
            return hit
    return _best(t, PROBLEMS)


def find_stage(text):
    return _best(normalize(text), STAGES)


def chemical_allowed(adv: dict, stage) -> bool:
    c = adv.get("chemical") or {}
    if c.get("reviewed") is not True:
        return False
    if any(c.get(f) in (None, "") for f in CHEM_FIELDS):
        return False
    return stage not in adv.get("block_chemical_stages", [])


def keyterms():
    terms = []
    for kws in list(CROPS.values()) + list(PROBLEMS.values()):
        for k in kws:
            if any("\u0c80" <= ch <= "\u0cff" for ch in k) and " " not in k and k not in terms:
                terms.append(k)
    return terms


@dataclass
class Reply:
    sentences: list
    end: bool = False
    sms: str = None
    meta: dict = field(default_factory=dict)


class Session:
    def __init__(self, escalation_number="1800-180-1551"):
        self.crop = self.problem = self.stage = None
        self.asks = {"crop": 0, "problem": 0, "stage": 0}
        self.advised = False
        self.last = None
        self.esc = escalation_number

    def _ask(self, slot):
        self.asks[slot] += 1
        if self.asks[slot] > 2:
            return self._escalate("too_many_clarifications")
        return self._remember(Reply(T["ask_" + slot], meta={"state": "ask_" + slot}))

    def _escalate(self, why):
        return Reply(T["escalate"] + T["bye"], end=True,
                     sms=f"ಕೃಷಿ ಮಿತ್ರ: ಹತ್ತಿರದ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ. {self.esc}",
                     meta={"state": "escalated", "why": why, "safety": "escalated"})

    def _remember(self, r):
        self.last = r
        return r

    def respond(self, text: str) -> Reply:
        t = normalize(text)
        if self.advised and any(normalize(k) in t for k in REPEAT) and self.last:
            return self.last
        if any(normalize(k) in t for k in GOODBYE) and (self.advised or not (self.crop or self.problem)):
            return Reply(T["bye"], end=True, meta={"state": "bye"})

        crop = find_crop(t)
        prob = find_problem(t, crop or self.crop)
        if prob and (self.crop is None or crop is None):
            if self.crop is None or KB[prob]["crop"] == self.crop:
                self.problem = prob
        elif prob:
            self.problem = prob
        if crop:
            if self.problem and KB[self.problem]["crop"] != crop:
                self.problem = None
            self.crop = crop
        if self.problem and not self.crop:
            self.crop = KB[self.problem]["crop"]
        st = find_stage(t)
        if st:
            self.stage = st

        if not self.crop:
            return self._ask("crop")
        if not self.problem:
            return self._ask("problem")
        adv = KB[self.problem]
        if adv["needs_stage"] and not self.stage:
            return self._ask("stage")
        return self._advise(adv)

    def _advise(self, adv):
        stage_key = self.stage if self.stage in adv["advice_kn"] else "default"
        s = [f"ನೀವು {CROP_KN[adv['crop']]} ಬೆಳೆಯ {adv['name_kn']} ಬಗ್ಗೆ ಕೇಳುತ್ತಿದ್ದೀರಿ ಎಂದು ಅರ್ಥವಾಯಿತು."]
        s += adv["advice_kn"][stage_key]
        if self.stage in adv.get("block_chemical_stages", []):
            safety = "chemical_blocked_stage"
        elif chemical_allowed(adv, self.stage):
            c = adv["chemical"]
            s += [f"ಶಿಫಾರಸು ಮಾಡಿದ ಔಷಧ {c['product']}. ಪ್ರಮಾಣ {c['dose']}. ನೀರಿನ ಪ್ರಮಾಣ {c['water']}.",
                  f"ಕೊಯ್ಲಿಗೆ ಮೊದಲು {c['preharvest_days']} ದಿನ ಕಾಯಿರಿ."] + T["safety"]
            safety = "chemical_approved"
        else:
            s += T["no_chem"]
            safety = "chemical_unreviewed"
        s += T["bye"]
        self.advised = True
        sms = (f"ಕೃಷಿ ಮಿತ್ರ ಸಲಹೆ\nಬೆಳೆ: {CROP_KN[adv['crop']]}\nಸಮಸ್ಯೆ: {adv['name_kn']}\n"
               + " ".join(adv["advice_kn"][stage_key]))
        return self._remember(Reply(s, sms=sms, meta={"state": "advised", "advisory_id": adv["id"], "safety": safety,
                                                     "crop": self.crop, "stage": self.stage}))
