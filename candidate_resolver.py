# ============================================================
# candidate_resolver.py
# ============================================================

import json
import re

from difflib import SequenceMatcher


# ============================================================
# NORMALIZE NAME
# ============================================================

def normalize_name(
    name: str
) -> str:

    if not name:
        return ""

    name = str(
        name
    ).strip().lower()

    # Remove extra spaces
    name = re.sub(
        r"\s+",
        " ",
        name
    )

    return name


# ============================================================
# NAME SIMILARITY
# ============================================================

def name_similarity(
    name1: str,
    name2: str
) -> float:

    return SequenceMatcher(
        None,
        normalize_name(name1),
        normalize_name(name2)
    ).ratio()


# ============================================================
# FIND BEST CANDIDATE
# ============================================================

def find_best_candidate(
    candidate_result,
    requested_name: str
):

    output = candidate_result.get(
        "output"
    )

    # --------------------------------------------------------
    # No output
    # --------------------------------------------------------

    if output is None:
        return None

    # --------------------------------------------------------
    # Oracle output may be JSON string
    # --------------------------------------------------------

    if isinstance(
        output,
        str
    ):

        try:

            output = json.loads(
                output
            )

        except json.JSONDecodeError:

            return None

    # --------------------------------------------------------
    # Get result
    # --------------------------------------------------------

    result = output.get(
        "result",
        {}
    )

    candidates = result.get(
        "requisitions",
        []
    )

    if not isinstance(
        candidates,
        list
    ):

        return None

    # --------------------------------------------------------
    # Normalize requested name
    # --------------------------------------------------------

    requested_normalized = (
        normalize_name(
            requested_name
        )
    )

    # ========================================================
    # 1. EXACT CASE-INSENSITIVE MATCH
    # ========================================================

    for candidate in candidates:

        actual_name = candidate.get(
            "CandidateName"
        )

        if not actual_name:
            continue

        if (
            normalize_name(
                actual_name
            )
            ==
            requested_normalized
        ):

            return {

                "status":
                    "EXACT",

                "candidate":
                    candidate,

                "score":
                    1.0
            }

    # ========================================================
    # 2. FUZZY MATCH
    # ========================================================

    best_candidate = None

    best_score = 0.0

    for candidate in candidates:

        actual_name = candidate.get(
            "CandidateName"
        )

        if not actual_name:
            continue

        score = name_similarity(
            requested_name,
            actual_name
        )

        if score > best_score:

            best_score = score

            best_candidate = candidate

    # ========================================================
    # 3. SUGGESTION
    # ========================================================

    if (
        best_candidate
        and
        best_score >= 0.75
    ):

        return {

            "status":
                "SUGGEST",

            "candidate":
                best_candidate,

            "score":
                best_score
        }

    # ========================================================
    # 4. NOT FOUND
    # ========================================================

    return None


# ============================================================
# RESOLVE CANDIDATE
# ============================================================

def resolve_candidate(
    candidate_result,
    requested_name: str
):

    match = find_best_candidate(
        candidate_result,
        requested_name
    )

    # --------------------------------------------------------
    # Candidate does not exist
    # --------------------------------------------------------

    if not match:

        return {

            "status":
                "NOT_FOUND",

            "candidate":
                None,

            "candidate_name":
                None,

            "email":
                None,

            "jobApplicationId":
                None,

            "score":
                0.0
        }

    # --------------------------------------------------------
    # Candidate found / suggested
    # --------------------------------------------------------

    candidate = match[
        "candidate"
    ]

    return {

        "status":
            match[
                "status"
            ],

        "candidate":
            candidate,

        "candidate_name":
            candidate.get(
                "CandidateName"
            ),

        "email":
            candidate.get(
                "Email"
            ),

        "jobApplicationId":
            candidate.get(
                "JobApplicationId"
            ),

        "score":
            match.get(
                "score",
                0.0
            )
    }