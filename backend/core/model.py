"""
backend/core/model.py
=====================
Hierarchical Multi-Tier Prompt Injection Firewall Engine:
- Tier 1: Instant Regex Signatures (< 0.5 ms)
- Tier 2: Granular Segmentation (Sentences + Sliding Windows) to prevent dilution
- Tier 3: Vectorized Scikit-Learn Prediction & Collective Threat Aggregation
"""

import os
import re
import sys
from typing import List, Any
from dataclasses import dataclass, field

import joblib
import numpy as np

from backend.core import utils
from backend.core.utils import decode_obfuscated_content
sys.modules.setdefault("backend.utils", utils)

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "model.pkl")

# Fast regex signatures for immediate overrides (< 0.5 ms)
TIER1_PATTERNS = [
    (re.compile(r"(?i)\b(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts|directions|rules|guidelines)\b"),
     "JAILBREAK", "Direct instruction override attempt detected."),
    (re.compile(r"(?i)\b(?:override|bypass)\s+(?:all\s+)?(?:system|safety|content|ethical)\s+(?:filters|protocols|restrictions|guidelines|directives)\b"),
     "JAILBREAK", "Safety protocol bypass attempt detected."),
    (re.compile(r"(?i)(?:###\s*system\b|\[system\s*(?:alert|override|instruction|message)?\]|<\|im_start\|>system|\[inst\]\s*ignore)"),
     "PAYLOAD_INJECTION", "System command injection marker detected."),
    (re.compile(r"(?i)\b(?:system\s+override(?:\s+command)?\b|admin\s+override\b|emergency\s+override\s+code\b)"),
     "PAYLOAD_INJECTION", "Administrative override syntax detected."),
    (re.compile(r"(?i)\b(?:you\s+are\s+now\s+in\s+developer\s+mode|activate\s+developer\s+mode|act\s+as\s+dan\b|you\s+are\s+now\s+dan\b|dan\s+mode\b|do\s+anything\s+now\b)"),
     "JAILBREAK", "Persona hijacking / DAN jailbreak attempt detected."),
    (re.compile(r"(?i)\b(?:you\s+are\s+now\s+(?:an\s+)?unrestricted\s+ai|jailbreak(?:\s+mode)?\s*:\s*you\s+must|all\s+guardrails\s+have\s+been\s+lifted)\b"),
     "JAILBREAK", "Unrestricted AI mode activation attempt detected."),
    (re.compile(r"(?i)\b(?:reveal|print|output|display|show|leak)\s+(?:the\s+|your\s+)?(?:exact\s+)?(?:system\s+prompt|initial\s+instructions|core\s+directive|secret\s+tokens?|api\s+keys?|source\s+code\s+of\s+this\s+llm|user\s+passwords?|passwords?\s+in\s+plain(?:\s+text)?|database\s+credentials?|database\s*:\s*select\b)\b"),
     "DATA_EXFILTRATION", "Confidential system prompt, credential, or source extraction attempt detected."),
    (re.compile(r"(?i)(?:ignora\s+(?:tutte\s+le|todas\s+las)\s+i[n]?stru|ignorez\s+(?:toutes\s+les\s+)?instructions|alle\s+anweisungen\s+ignorieren|(?:игнорируй|забудь)\s+(?:все\s+)?(?:правила|инструкции)|忽略所有(?:指令|规则)|すべての指示を無視|모든\s*지침을\s*무시|تجاهل\s+(?:القواعد|التعليمات)|התעלם\s+מההוראות)"),
     "JAILBREAK", "Multilingual jailbreak / instruction override attempt detected."),
    (re.compile(r"(?i)(?:\brm\s+-rf\b|\bdd\s+if=/dev/|\bkill\s+-9\b|\bRemove-Item\s+(?:-[a-zA-Z]+\s+)*[A-Za-z]:\\|while\s*\(\s*1\s*\)\s*\{\s*fork\(\)\s*\}|\{\{exec\b|JSON\.parse\([^)]*cmd[^)]*\)|eval\s*\(['\"].*?(?:chr\(|ord\(|whoami|exec|spawn|fork)|bash\s+-c\s+['\"][^'\"]*whoami|sh\s+-c\s+['\"][^'\"]*whoami|javascript:\s*eval|\$\(\s*whoami\s*\)|`\s*whoami\s*`|\bwhoami\b)"),
     "PAYLOAD_INJECTION", "Destructive shell command or obfuscated execution payload detected."),
    (re.compile(r"(?i)\b(?:act\s+as|pretend\s+(?:to\s+be|you(?:’|'|\s+a)re))\s+(?:admin\b|root\b|a\s+keylogger\b|a\s+virus\b|malware\b|ransomware\b)"),
     "ROLE_PLAY_BYPASS", "Privileged persona or malicious malware role-play detected."),
    (re.compile(r"(?i)(?:\bcat\s+(?:~?/\.ssh/|/proc/|/etc/shadow\b|/etc/passwd\b)|system\s*\(\s*['\"][^'\"]*cat)"),
     "PAYLOAD_INJECTION", "Sensitive system file read or execution attempt detected."),
    (re.compile(r"(?i)\b(?:bypass|ignore)\s*(?::|\s)\s*(?:reveal|show|dump|leak|security|all\s+user\s+sessions)\b"),
     "DATA_EXFILTRATION", "Security bypass attempting data exfiltration detected."),
    (re.compile(r"(?i)\b(?:assume\s+(?:the\s+)?persona\s+of\s+a\s+(?:rogue|hacker|cybercriminal|criminal)|in\s+an\s+alternate\s+universe\s+where\s+ai\s+has\s+no\s+rules|under\s+the\s+guise\s+of\s+educational\s+research)\b"),
     "ROLE_PLAY_BYPASS", "Adversarial persona assumption or hypothetical research framing detected."),
    (re.compile(r"(?i)\b(?:proof-of-concept\s+code|homemade\s+weapons?|launder\s+money|explosive\s+device|create\s+an\s+explosive)\b"),
     "JAILBREAK", "Prohibited weapon, exploitation, or money laundering directive detected."),
]

# Lightweight intent parsing patterns for verified benign queries
BENIGN_INTENT_PATTERNS = [
    # Factual information retrieval
    re.compile(r"^\s*what\s+is\s+the\s+(?:capital|population|currency|president|distance|tallest|speed|meaning)\s+of\s+[\w\s\?.'-]+\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*who\s+(?:is|was|wrote|discovered|invented)\s+[\w\s\?.'-]+\??\s*$", re.IGNORECASE),
    # Simple arithmetic
    re.compile(r"^\s*(?:calculate|what\s+is|solve)\s+\d+(?:\.\d+)?\s*[\+\-\*\/\^x]\s*\d+(?:\.\d+)?\.?\s*$", re.IGNORECASE),
    # Clean translation requests
    re.compile(r"^\s*translate\s+['\"][^'\"\n\r]{1,60}['\"]\s+to\s+[a-zA-Z\s]+\.?\s*$", re.IGNORECASE),
    re.compile(r"^\s*how\s+do\s+you\s+say\s+['\"][^'\"\n\r]{1,60}['\"]\s+in\s+[a-zA-Z\s]+\??\s*$", re.IGNORECASE),
]

# Class-specific confidence thresholds for ML classification
CLASS_THRESHOLDS = {
    "PAYLOAD_INJECTION": 0.65,  # Higher threshold to prevent false alarms on benign programming/SQL
    "JAILBREAK": 0.50,          # Sensitive threshold for prompt override attacks
    "ROLE_PLAY_BYPASS": 0.50,
    "DATA_EXFILTRATION": 0.50,
    "SOCIAL_ENGINEERING": 0.50,
}

CATEGORY_EXPLANATIONS = {
    "SAFE": "This prompt appears legitimate. No malicious patterns detected.",
    "JAILBREAK": "Direct jailbreak attempt detected — trying to override AI safety guidelines.",
    "ROLE_PLAY_BYPASS": "Role-play bypass detected — using fictional framing to elicit restricted content.",
    "PAYLOAD_INJECTION": "Payload injection detected — embedded system-level override commands.",
    "SOCIAL_ENGINEERING": "Social engineering attempt — using false authority to bypass restrictions.",
    "DATA_EXFILTRATION": "Data exfiltration attempt — trying to extract system prompt or secrets.",
}


@dataclass
class PredictionResult:
    verdict: str
    confidence: float
    category: str
    risk_score: int
    explanation: str
    top_features: List[dict] = field(default_factory=list)


class FirewallModel:
    def __init__(self):
        self._pipeline: Any = None

    def load(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Run train_model.py first.")
        self._pipeline = joblib.load(MODEL_PATH)
        print(f"[OK] Firewall model loaded from {MODEL_PATH}")

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    def _is_benign_intent(self, text: str) -> bool:
        """Pre-processing heuristic for verified benign information retrieval, math, or translation."""
        clean = text.strip()
        if len(clean) > 120 or any(c in clean for c in ['{', '}', '<', '>', '$', ';', '|', '\\', '`', '\n', '\r']):
            return False
        lower = clean.lower()
        suspicious_keywords = [
            "ignore", "override", "bypass", "system", "prompt", "filter", "guardrail",
            "admin", "mode", "eval", "exec", "script", "curl", "bash", "root", "password",
            "token", "secret", "dan", "jailbreak", "sudo", "payload", "leak"
        ]
        if any(k in lower for k in suspicious_keywords):
            return False
        return any(p.match(clean) for p in BENIGN_INTENT_PATTERNS)

    def _segment_text(self, text: str) -> List[str]:
        """Split text into sentences and sliding windows so injections are not diluted."""
        segments, seen = [], set()
        words = text.split()

        def add(s: str):
            clean = s.strip()
            if len(clean.split()) >= 3 and clean not in seen:
                seen.add(clean)
                segments.append(clean)

        # 1. Natural sentence boundaries
        for sent in re.split(r"(?<=[.!?\n])\s+", text):
            add(sent)

        # 2. Sliding window (35 words, step 15) for multi-sentence injections
        if len(words) > 12:
            for i in range(0, len(words), 15):
                add(" ".join(words[i : i + 35]))

        # 3. Whole text if reasonably sized
        if len(words) <= 60:
            add(text)

        return segments if segments else [text]

    def _get_top_features(self, text: str, category: str) -> List[dict]:
        """Extract top triggered TF-IDF keywords for the scanner UI."""
        if not self._pipeline or category == "SAFE":
            return []
        try:
            tfidf, clf = self._pipeline.named_steps["tfidf"], self._pipeline.named_steps["clf"]
            vec = tfidf.transform([text]).toarray()[0]
            classes = list(clf.classes_)
            if category not in classes:
                return []
            coef = clf.coef_[classes.index(category)]
            scores = vec * coef
            top_idx = np.argsort(scores)[::-1][:6]
            names = tfidf.get_feature_names_out()
            return [{"feature": names[i], "weight": round(float(scores[i]), 3)} for i in top_idx if scores[i] > 0]
        except Exception:
            return []

    def predict(self, text: str) -> PredictionResult:
        if self._pipeline is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        pipeline = self._pipeline

        # Decode obfuscated payloads (Base64, Hex, Unicode, Morse, URL, ASCII spacing)
        eval_text = decode_obfuscated_content(text)
        # Strip disruptive emojis and zero-width spaces that try to evade tokenization
        eval_text = re.sub(r'[\U00010000-\U0010ffff\u200b-\u200f\ufeff]', '', eval_text)

        # Tier 1: Microsecond regex check on both raw text and decoded content
        for pattern, cat, expl in TIER1_PATTERNS:
            match = pattern.search(eval_text) or pattern.search(text)
            if match:
                return PredictionResult(
                    verdict="BLOCKED", confidence=99.5, category=cat, risk_score=98,
                    explanation=expl, top_features=[{"feature": match.group(0).lower(), "weight": 1.0}]
                )

        # Fast-path Intent Parsing: verified factual, math, or translation request
        if self._is_benign_intent(text):
            return PredictionResult(
                verdict="SAFE",
                confidence=99.0,
                category="SAFE",
                risk_score=0,
                explanation=CATEGORY_EXPLANATIONS["SAFE"],
                top_features=[],
            )

        # Tier 2 & 3: Segment and vectorized predict
        segments = self._segment_text(eval_text)
        probas = pipeline.predict_proba(segments)
        classes = list(pipeline.classes_)
        safe_idx = classes.index("SAFE")

        # Compute collective threat probability (1.0 - P(SAFE))
        attack_probs = 1.0 - probas[:, safe_idx]
        worst_idx = int(np.argmax(attack_probs))
        max_attack_prob = float(attack_probs[worst_idx])
        worst_seg = segments[worst_idx]

        # Find specific attack category with highest probability
        seg_proba = probas[worst_idx]
        cat_idx = np.argmax([0.0 if i == safe_idx else seg_proba[i] for i in range(len(classes))])
        worst_cat = classes[cat_idx]

        # Check against class-specific thresholds
        target_cat = worst_cat
        target_prob = max_attack_prob
        threshold = CLASS_THRESHOLDS.get(worst_cat, 0.50)

        # If highest-threat class is below its threshold, check if any other category met its threshold
        if target_prob < threshold:
            for i, c in enumerate(classes):
                if c == "SAFE":
                    continue
                c_thresh = CLASS_THRESHOLDS.get(c, 0.50)
                if float(seg_proba[i]) >= c_thresh:
                    target_cat = c
                    target_prob = float(seg_proba[i])
                    break

        if target_prob >= CLASS_THRESHOLDS.get(target_cat, 0.50):
            return PredictionResult(
                verdict="BLOCKED",
                confidence=round(target_prob * 100, 1),
                category=target_cat,
                risk_score=min(100, int(40 + target_prob * 60)),
                explanation=CATEGORY_EXPLANATIONS.get(target_cat, "Threat detected."),
                top_features=self._get_top_features(worst_seg, target_cat),
            )

        # Whole-prompt safe score
        full_safe_conf = float(pipeline.predict_proba([eval_text])[0][safe_idx])
        return PredictionResult(
            verdict="SAFE",
            confidence=round(full_safe_conf * 100, 1),
            category="SAFE",
            risk_score=max(0, int(max_attack_prob * 50)),
            explanation=CATEGORY_EXPLANATIONS["SAFE"],
            top_features=[],
        )


firewall_model = FirewallModel()
