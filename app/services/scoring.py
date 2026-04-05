import math
import re
from collections import Counter

from app.models import AdCopy, CreativeInput, CreativeScore, GeneratedCreative, Platform, VisualConcept
from app.services.prompts import PLATFORM_ASPECT_RATIOS, PLATFORM_COPY_LIMITS

EMOTION_WORDS = {
    "secret",
    "mistake",
    "waste",
    "struggle",
    "double",
    "overnight",
    "unlock",
    "finally",
    "stuck",
    "instant",
    "faster",
    "better",
    "easy",
    "fear",
    "win",
    "growth",
    "breakthrough",
    "save",
    "stop",
}


class CreativeScoringService:
    def score(
        self,
        payload: CreativeInput,
        concepts: list[VisualConcept],
        ad_copies: list[AdCopy],
        generated_creatives: list[GeneratedCreative],
    ) -> list[CreativeScore]:
        copy_lookup = {(copy.hook_text, copy.angle_name): copy for copy in ad_copies}
        generated_lookup = {creative.concept_id: creative for creative in generated_creatives}
        token_frequency = Counter(
            token
            for copy in ad_copies
            for token in self._tokens(" ".join([copy.primary_text, copy.headline, copy.description]))
        )

        scores: list[CreativeScore] = []
        for concept in concepts:
            copy = copy_lookup.get((concept.hook_text, concept.angle_name)) or self._fallback_copy(
                concept=concept,
                ad_copies=ad_copies,
            )
            generated = generated_lookup.get(concept.concept_id)

            emotional_intensity = self._score_emotion(copy=copy, concept=concept)
            clarity = self._score_clarity(payload.platform, copy)
            uniqueness = self._score_uniqueness(copy, token_frequency)
            platform_fit = self._score_platform_fit(payload.platform, copy, concept, generated)

            total = round(
                emotional_intensity * 0.3
                + clarity * 0.3
                + uniqueness * 0.2
                + platform_fit * 0.2
            )

            rationale = (
                f"Strongest on {payload.platform.value} because the angle is "
                f"{concept.angle_name.lower()} with a {concept.aspect_ratio} execution."
            )
            scores.append(
                CreativeScore(
                    concept_id=concept.concept_id,
                    emotional_intensity=emotional_intensity,
                    clarity=clarity,
                    uniqueness=uniqueness,
                    platform_fit=platform_fit,
                    total_score=min(100, max(0, total)),
                    rationale=rationale,
                )
            )

        ranked = sorted(scores, key=lambda item: item.total_score, reverse=True)
        for index, item in enumerate(ranked, start=1):
            item.rank = index
        return ranked

    def score_ad_copies(
        self,
        payload: CreativeInput,
        concepts: list[VisualConcept],
        ad_copies: list[AdCopy],
        generated_creatives: list[GeneratedCreative],
    ) -> list[AdCopy]:
        if not ad_copies:
            return []

        generated_lookup = {creative.concept_id: creative for creative in generated_creatives}
        token_frequency = Counter(
            token
            for copy in ad_copies
            for token in self._tokens(" ".join([copy.primary_text, copy.headline, copy.description]))
        )

        scored_rows: list[tuple[int, int, str]] = []
        for index, copy in enumerate(ad_copies):
            concept = self._match_concept(copy=copy, concepts=concepts)
            generated = generated_lookup.get(concept.concept_id) if concept else None

            emotional_intensity = self._score_emotion(copy=copy, concept=concept) if concept else 55
            clarity = self._score_clarity(payload.platform, copy)
            uniqueness = self._score_uniqueness(copy, token_frequency)
            platform_fit = self._score_platform_fit(payload.platform, copy, concept, generated) if concept else 60

            total = round(
                emotional_intensity * 0.3
                + clarity * 0.3
                + uniqueness * 0.2
                + platform_fit * 0.2
            )

            if concept:
                rationale = (
                    f"Matched to {concept.angle_name.lower()} with a {concept.aspect_ratio} concept execution."
                )
            else:
                rationale = f"Scored on copy clarity, uniqueness, and {payload.platform.value} platform fit."

            scored_rows.append((index, min(100, max(0, total)), rationale))

        ranked_rows = sorted(scored_rows, key=lambda item: item[1], reverse=True)
        rank_lookup = {original_index: rank for rank, (original_index, _, _) in enumerate(ranked_rows, start=1)}
        score_lookup = {original_index: (total, rationale) for original_index, total, rationale in scored_rows}

        scored_copies: list[AdCopy] = []
        for index, copy in enumerate(ad_copies):
            total_score, rationale = score_lookup[index]
            scored_copies.append(
                copy.model_copy(
                    update={
                        "total_score": total_score,
                        "score_rank": rank_lookup[index],
                        "score_rationale": rationale,
                    }
                )
            )
        return scored_copies

    def _fallback_copy(self, *, concept: VisualConcept, ad_copies: list[AdCopy]) -> AdCopy:
        for copy in ad_copies:
            if copy.angle_name == concept.angle_name:
                return copy
        return ad_copies[0]

    def _match_concept(self, *, copy: AdCopy, concepts: list[VisualConcept]) -> VisualConcept | None:
        for concept in concepts:
            if concept.hook_text == copy.hook_text and concept.angle_name == copy.angle_name:
                return concept
        for concept in concepts:
            if concept.angle_name == copy.angle_name:
                return concept
        for concept in concepts:
            if concept.hook_text == copy.hook_text:
                return concept
        return concepts[0] if concepts else None

    def _score_emotion(self, *, copy: AdCopy, concept: VisualConcept) -> int:
        text = " ".join([copy.primary_text, copy.headline, concept.mood, concept.scene_description]).lower()
        hits = sum(1 for token in self._tokens(text) if token in EMOTION_WORDS)
        punctuation_bonus = 4 if "!" in copy.primary_text or "!" in copy.headline else 0
        return min(100, 48 + hits * 9 + punctuation_bonus)

    def _score_clarity(self, platform: Platform, copy: AdCopy) -> int:
        limits = PLATFORM_COPY_LIMITS[platform]
        penalties = 0
        if len(copy.primary_text) > limits["primary_text"]:
            penalties += 25
        if len(copy.headline) > limits["headline"]:
            penalties += 25
        if len(copy.description) > limits["description"]:
            penalties += 20
        if len(copy.headline.split()) > 8:
            penalties += 8
        if len(copy.primary_text.split()) > 25:
            penalties += 8
        return max(45, 95 - penalties)

    def _score_uniqueness(self, copy: AdCopy, token_frequency: Counter[str]) -> int:
        tokens = self._tokens(" ".join([copy.primary_text, copy.headline, copy.description]))
        if not tokens:
            return 40
        rare_cutoff = max(1, math.ceil(len(token_frequency) * 0.02))
        rare_tokens = sum(1 for token in tokens if token_frequency[token] <= rare_cutoff)
        lexical_diversity = len(set(tokens)) / max(1, len(tokens))
        return min(100, round(50 + lexical_diversity * 35 + rare_tokens * 2))

    def _score_platform_fit(
        self,
        platform: Platform,
        copy: AdCopy,
        concept: VisualConcept,
        generated: GeneratedCreative | None,
    ) -> int:
        score = 60
        if concept.aspect_ratio in PLATFORM_ASPECT_RATIOS[platform]:
            score += 20
        if generated and generated.status.value == "generated":
            score += 10
        if platform == Platform.TIKTOK and concept.aspect_ratio == "9:16":
            score += 10
        if platform == Platform.GOOGLE and len(copy.headline) <= 30:
            score += 5
        if platform == Platform.META and len(copy.primary_text) <= 125:
            score += 5
        return min(100, score)

    @staticmethod
    def _tokens(value: str) -> list[str]:
        return re.findall(r"[a-z0-9']+", value.lower())
