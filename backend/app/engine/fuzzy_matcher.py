"""
Heuristic entity resolution using fuzzy string matching.

Per document §4.1:
  - Uses Levenshtein distance (via RapidFuzz) to match incoming
    bulk/block deal client names against known fund aliases.
  - Threshold: 85% similarity score for automatic classification.
  - Logs near-misses (70-84%) for manual review.
"""

from typing import Optional, Tuple, List
from rapidfuzz import fuzz, process

from app.core.fund_registry import ALL_FUNDS, ALIAS_TO_FUND_ID, FundConfig
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# Near-miss threshold for logging potential matches that need review
NEAR_MISS_THRESHOLD = 70


class FundMatcher:
    """
    Matches incoming client names from exchange APIs against the
    known fund alias dictionary using fuzzy string matching.
    """

    def __init__(self):
        # Build flat list of (alias, fund_id) for fuzzy matching
        self._alias_list: List[Tuple[str, str]] = []
        for fund in ALL_FUNDS:
            for alias in fund.aliases:
                self._alias_list.append((alias.upper(), fund.fund_id))

        # Extract just the alias strings for rapidfuzz.process
        self._alias_strings = [a[0] for a in self._alias_list]
        self._alias_to_fund = {a[0]: a[1] for a in self._alias_list}

        logger.info(
            "FundMatcher initialized with %d aliases across %d funds.",
            len(self._alias_list), len(ALL_FUNDS)
        )

    def match(self, client_name: str) -> Optional[str]:
        """
        Match a client name against known fund aliases.

        Args:
            client_name: The raw clientName from an exchange bulk/block deal.

        Returns:
            fund_id if a match is found with ≥85% confidence, else None.
        """
        if not client_name:
            return None

        normalized = client_name.strip().upper()

        # Step 1: Try exact match first (fastest)
        if normalized in ALIAS_TO_FUND_ID:
            fund_id = ALIAS_TO_FUND_ID[normalized]
            logger.debug("Exact match: '%s' → %s", client_name, fund_id)
            return fund_id

        # Step 2: Fuzzy match using token_sort_ratio
        # token_sort_ratio handles word reordering: "FUND GROWTH NEXUS" ≈ "NEXUS GROWTH FUND"
        result = process.extractOne(
            normalized,
            self._alias_strings,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=NEAR_MISS_THRESHOLD,
        )

        if result is None:
            return None

        matched_alias, score, _ = result
        fund_id = self._alias_to_fund[matched_alias]

        if score >= settings.FUZZY_MATCH_THRESHOLD:
            logger.info(
                "Fuzzy match (%.1f%%): '%s' → %s (matched alias: '%s')",
                score, client_name, fund_id, matched_alias
            )
            return fund_id
        else:
            # Near miss — log for manual review
            logger.warning(
                "Near miss (%.1f%% < %d%% threshold): '%s' ~ '%s' [%s]. Manual review needed.",
                score, settings.FUZZY_MATCH_THRESHOLD, client_name, matched_alias, fund_id
            )
            return None

    def match_with_score(self, client_name: str) -> Tuple[Optional[str], float]:
        """
        Like match(), but also returns the confidence score.
        Useful for debugging and reporting.
        """
        if not client_name:
            return None, 0.0

        normalized = client_name.strip().upper()

        if normalized in ALIAS_TO_FUND_ID:
            return ALIAS_TO_FUND_ID[normalized], 100.0

        result = process.extractOne(
            normalized,
            self._alias_strings,
            scorer=fuzz.token_sort_ratio,
        )

        if result is None:
            return None, 0.0

        matched_alias, score, _ = result
        fund_id = self._alias_to_fund[matched_alias]

        if score >= settings.FUZZY_MATCH_THRESHOLD:
            return fund_id, score
        else:
            return None, score

    def get_all_matches(self, client_name: str, limit: int = 5) -> List[Tuple[str, str, float]]:
        """
        Return all potential matches with scores, for debugging.
        Returns list of (fund_id, matched_alias, score).
        """
        if not client_name:
            return []

        normalized = client_name.strip().upper()
        results = process.extract(
            normalized,
            self._alias_strings,
            scorer=fuzz.token_sort_ratio,
            limit=limit,
        )

        return [
            (self._alias_to_fund[alias], alias, score)
            for alias, score, _ in results
        ]


# Module-level singleton for convenience
_matcher: Optional[FundMatcher] = None


def get_matcher() -> FundMatcher:
    """Get or create the module-level FundMatcher singleton."""
    global _matcher
    if _matcher is None:
        _matcher = FundMatcher()
    return _matcher


def match_fund(client_name: str) -> Optional[str]:
    """
    Convenience function: match a client name to a fund_id.
    Returns fund_id if match ≥85%, else None.
    """
    return get_matcher().match(client_name)
