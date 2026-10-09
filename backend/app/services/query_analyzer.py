import re

from app.core.text_matching import (
    contains_any,
    count_matches,
)
from app.schemas.query_analysis import (
    LegalDomain,
    LegalIntent,
    QueryAnalysis,
    UrgencyLevel,
)


class QueryAnalyzer:

    IMMEDIATE_VIOLENT_THREAT_PATTERN = re.compile(
        r"(?=.*\b(?:threatening|threatens?|threatened)\b)"
        r"(?=.*\b(?:kill|murder|attack|hurt|harm)\b)"
        r"(?=.*\b(?:me|us)\b)"
        r"(?=.*\b(?:right now|currently|at this moment)\b)",
        re.IGNORECASE,
    )

    # IMPORTANT:
    # These phrases indicate an immediate or potentially life-threatening
    # situation. Keep this list intentionally narrow to reduce false
    # emergency classifications.
    #
    # Do NOT add broad cybercrime terms such as:
    # "hacked", "phishing", "online fraud", "otp", "cybercrime"
    # because those situations are not automatically physical emergencies.
    EMERGENCY_KEYWORDS = {
        # General emergencies
        "emergency",
        "dying",
        "bleeding",
        "unconscious",
        "life threatening",
        "life-threatening",
        "hostage",
        "attack happening",
        "being attacked",
        "attacking me",
        "someone attacking",
        "someone is attacking",
        "immediate danger",
        "danger right now",
        "under attack",

        # Fire emergencies
        "there is a fire",
        "there's a fire",
        "fire right now",
        "fire emergency",
        "building on fire",
        "house on fire",
        "car on fire",
        "vehicle on fire",

        # Medical emergencies
        "not breathing",
        "heart attack",
        "stroke",
        "severe injury",
        "medical emergency",
        "medical emergency right now",
        "person is unconscious",
        "someone is unconscious",

        # Child-safety emergencies
        "child kidnapped",
        "child is kidnapped",
        "missing child",
        "child is missing",

        # Immediate personal-safety emergencies
        "sexual assault happening",
        "being assaulted",
        "someone is threatening me right now",
        "someone is trying to kill me",
        "someone is trying to hurt me",
        "someone is breaking into my house",
        "someone broke into my house",
        "home invasion",
    }

    URGENT_KEYWORDS = {
        "threat",
        "threatened",
        "violence",
        "abuse",
        "harassment",
        "stalking",
        "blackmail",
        "urgent",
        "immediately",
    }

    CRIMINAL_KEYWORDS = {
        "bns",
        "bharatiya nyaya sanhita",
        "theft",
        "stolen",
        "stealing",
        "steal",
        "stole",
        "robbery",
        "murder",
        "assault",
        "physical assault",
        "criminal force",
        "hit me",
        "intentionally hit",
        "caused hurt",
        "criminal",
        "fraud",
        "threat",
        "kidnap",
        "rape",
        "cheating",
        "trespass",
        "crime",
        "fir",
        "police",
    }

    PROPERTY_KEYWORDS = {
        "property",
        "land",
        "house",
        "flat",
        "apartment",
        "rent",
        "rental",
        "landlord",
        "tenant",
        "lease",
        "eviction",
        "deposit",
    }

    EMPLOYMENT_KEYWORDS = {
        "job",
        "employer",
        "employee",
        "salary",
        "wages",
        "termination",
        "fired",
        "dismissed",
        "workplace",
        "employment",
        "overtime",
    }

    CONSUMER_KEYWORDS = {
        "consumer",
        "product",
        "defective",
        "refund",
        "seller",
        "shop",
        "purchase",
        "warranty",
        "service",
        "customer",
    }

    CYBER_KEYWORDS = {
        "cyber",
        "hacked",
        "hack",
        "phishing",
        "online fraud",
        "otp",
        "password stolen",
        "account hacked",
        "instagram hacked",
        "email hacked",
        "cybercrime",
    }

    TRAFFIC_KEYWORDS = {
        "traffic",
        "vehicle",
        "car",
        "bike",
        "motorcycle",
        "driving",
        "license",
        "licence",
        "challan",
        "accident",
        "road",
    }

    FAMILY_KEYWORDS = {
        "marriage",
        "divorce",
        "husband",
        "wife",
        "child custody",
        "maintenance",
        "domestic",
        "family",
    }

    GOVERNMENT_KEYWORDS = {
        "government",
        "passport",
        "voter",
        "aadhaar",
        "ration card",
        "certificate",
        "government office",
        "municipality",
        "municipal",
    }

    # Clear public-service concepts that should route to
    # the civic pipeline even when the question also uses
    # generic procedure wording such as "how can I".
    #
    # Keep generic words such as "government" out of this
    # set so legal questions involving government action
    # are not automatically reclassified as civic services.
    CIVIC_SERVICE_KEYWORDS = {
        "public service",
        "government service",
        "government services",
        "civic service",
        "civic services",
        "municipal service",
        "municipal services",
        "water supply",
        "water-supply",
        "public water supply",
        "public water-supply",
        "municipal water",
        "government office",
        "public office",
        "passport",
        "voter",
        "aadhaar",
        "ration card",
        "certificate",
        "municipality",
        "municipal",
    }

    # Intentionally narrow, explicit requests that are
    # clearly unrelated to legal or civic assistance.
    # Ambiguous wording keeps the existing legal-routing
    # behavior instead of being rejected by default.
    OUT_OF_SCOPE_REQUEST_KEYWORDS = {
        "tell me a joke",
        "write a joke",
        "write me a joke",
        "make me laugh",
        "tell me a story",
        "write a story",
        "write me a story",
        "write a poem",
        "write me a poem",
        "weather forecast",
        "sports score",
        "movie recommendation",
        "music recommendation",
        "give me a recipe",
    }

    AUTHORITY_KEYWORDS = {
        "where can i report",
        "where should i report",
        "where do i report",
        "where can i file",
        "where should i file",
        "where do i file",
        "where to report",
        "where to file",
        "where can i complain",
        "where should i complain",
        "where do i complain",
        "where to complain",
        "where can i get legal aid",
        "where can i get free legal aid",
        "where can i apply for legal aid",
        "where should i apply for legal aid",
        "which authority",
        "which department",
        "which office",
        "who should i contact",
        "whom should i contact",
        "report to",
    }

    DOCUMENT_KEYWORDS = {
        "document",
        "documents",
        "proof",
        "evidence",
        "papers",
        "records",
        "what should i keep",
    }

    PROCEDURE_KEYWORDS = {
        "how do i",
        "how can i",
        "procedure",
        "process",
        "steps",
        "file",
        "register",
        "apply",
    }

    COMPLAINT_KEYWORDS = {
        "complaint",
        "complain",
        "file a complaint",
        "make a complaint",
        "lodge a complaint",
        "report a company",
        "report an employer",
    }

    JURISDICTIONS = {
        "assam": "AS",
        "maharashtra": "MH",
        "karnataka": "KA",
        "india": "IN",
    }

    # Queries containing these concepts are more likely
    # to depend on state/local rules or authorities.
    JURISDICTION_HINT_KEYWORDS = {
        "state",
        "local authority",
        "local law",
        "municipality",
        "municipal",
        "district",
        "police station",
        "police department",
        "rto",
        "transport department",
        "rent",
        "rental",
        "landlord",
        "tenant",
        "property",
        "land",
        "eviction",
        "traffic",
        "challan",
        "driving licence",
        "driving license",
    }

    CONSTITUTIONAL_KEYWORDS = {
        "constitution",
        "constitutional",
        "article",
        "preamble",
        "fundamental rights",
        "fundamental right",
        "fundamental duties",
        "fundamental duty",
        "directive principles",
        "directive principle",
        "equality before law",
        "right to life",
        "personal liberty",
        "freedom of speech",
        "freedom of speech and expression",
        "constitutional remedies",
        "seventh schedule",
        "amendment of the constitution",
    }

    RETRIEVAL_CONCEPT_ALIASES = {
        "theft": {
            "theft",
            "stealing",
            "steal",
            "stole",
            "stolen",
        },
        "assault or criminal force": {
            "assault",
            "physical assault",
            "criminal force",
            "hit me",
            "intentionally hit",
        },
    }

    PENALTY_QUERY_HINTS = {
        "punishment",
        "penalty",
        "sentence",
        "sentenced",
        "how many years",
        "what happens",
    }

    DEFINITION_QUERY_HINTS = {
        "what is",
        "define",
        "definition of",
        "meaning of",
    }

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(
            r"\s+",
            " ",
            text.lower().strip(),
        )

    @staticmethod
    def _contains_any(
        text: str,
        keywords: set[str],
    ) -> bool:
        """
        Safely check whether text contains any keyword or phrase.

        Matching is delegated to the shared boundary-aware
        text-matching utility.
        """
        return contains_any(
            text=text,
            keywords=keywords,
        )

    @staticmethod
    def _extract_keywords(
        text: str,
    ) -> list[str]:
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "what",
            "how",
            "can",
            "i",
            "do",
            "my",
            "me",
            "to",
            "for",
            "of",
            "and",
            "in",
            "on",
            "with",
            "under",
            "should",
            "where",
            "who",
            "which",
            "please",
            "tell",
        }

        tokens = re.findall(
            r"\b[a-zA-Z0-9]+\b",
            text.lower(),
        )

        return list(
            dict.fromkeys(
                token
                for token in tokens
                if token not in stop_words
                and len(token) > 2
            )
        )[:20]

    def _detect_urgency(
        self,
        text: str,
    ) -> UrgencyLevel:
        # Emergency always takes priority.
        if (
            self._contains_any(
                text,
                self.EMERGENCY_KEYWORDS,
            )
            or self.IMMEDIATE_VIOLENT_THREAT_PATTERN.search(
                text
            )
        ):
            return UrgencyLevel.EMERGENCY

        if self._contains_any(
            text,
            self.URGENT_KEYWORDS,
        ):
            return UrgencyLevel.URGENT

        return UrgencyLevel.NORMAL

    def _detect_domain(
        self,
        text: str,
    ) -> LegalDomain:
        """
        Determine the most likely legal domain using
        boundary-aware keyword scoring.

        Each matching keyword contributes one point.
        Boundary-aware matching prevents false positives such as:

        - "fir" matching "firewall"
        - "hack" matching "hackathon"
        - "car" matching "career"
        """
        if self._contains_any(
            text,
            self.CIVIC_SERVICE_KEYWORDS,
        ):
            return LegalDomain.GOVERNMENT_SERVICES

        domain_keywords = [
            (
                LegalDomain.CYBERCRIME,
                self.CYBER_KEYWORDS,
            ),
            (
                LegalDomain.CRIMINAL,
                self.CRIMINAL_KEYWORDS,
            ),
            (
                LegalDomain.PROPERTY,
                self.PROPERTY_KEYWORDS,
            ),
            (
                LegalDomain.EMPLOYMENT,
                self.EMPLOYMENT_KEYWORDS,
            ),
            (
                LegalDomain.CONSUMER,
                self.CONSUMER_KEYWORDS,
            ),
            (
                LegalDomain.TRAFFIC,
                self.TRAFFIC_KEYWORDS,
            ),
            (
                LegalDomain.FAMILY,
                self.FAMILY_KEYWORDS,
            ),
            (
                LegalDomain.CONSTITUTIONAL,
                self.CONSTITUTIONAL_KEYWORDS,
            ),
            (
                LegalDomain.GOVERNMENT_SERVICES,
                self.GOVERNMENT_KEYWORDS,
            ),
        ]

        scores = {
            domain: count_matches(
                text=text,
                keywords=keywords,
            )
            for domain, keywords in domain_keywords
        }

        best_domain = max(
            scores,
            key=scores.get,
        )

        if scores[best_domain] == 0:
            return LegalDomain.UNKNOWN

        return best_domain

    def _detect_intent(
        self,
        text: str,
        urgency: UrgencyLevel,
    ) -> LegalIntent:
        # Emergency must always take priority.
        if urgency == UrgencyLevel.EMERGENCY:
            return LegalIntent.EMERGENCY

        if self._contains_any(
            text,
            self.OUT_OF_SCOPE_REQUEST_KEYWORDS,
        ):
            return LegalIntent.OUT_OF_SCOPE

        # Authority lookup must take priority over
        # generic reporting/procedure language.
        if self._contains_any(
            text,
            self.AUTHORITY_KEYWORDS,
        ):
            return LegalIntent.AUTHORITY_LOOKUP

        # Explicit civic-service concepts must take
        # priority over complaint and generic procedure
        # wording. This keeps public-service complaints
        # out of legal RAG while preserving consumer and
        # employment complaint routing.
        if self._contains_any(
            text,
            self.CIVIC_SERVICE_KEYWORDS,
        ):
            return LegalIntent.GENERAL_CIVIC

        # Complaint-specific legal queries should not be
        # swallowed by generic procedure keywords.
        if self._contains_any(
            text,
            self.COMPLAINT_KEYWORDS,
        ):
            return LegalIntent.COMPLAINT_GUIDANCE

        if self._contains_any(
            text,
            self.DOCUMENT_KEYWORDS,
        ):
            return LegalIntent.DOCUMENT_GUIDANCE

        if self._contains_any(
            text,
            self.PROCEDURE_KEYWORDS,
        ):
            return LegalIntent.LEGAL_PROCEDURE

        if (
            "what is" in text
            or "what does" in text
            or "punishment" in text
            or "law" in text
            or "legal" in text
        ):
            return LegalIntent.LEGAL_INFORMATION

        if self._contains_any(
            text,
            self.GOVERNMENT_KEYWORDS,
        ):
            return LegalIntent.GENERAL_CIVIC

        return LegalIntent.LEGAL_INFORMATION

    @staticmethod
    def _detect_jurisdiction(
        text: str,
    ) -> str | None:
        for name, code in QueryAnalyzer.JURISDICTIONS.items():
            if re.search(
                rf"\b{re.escape(name)}\b",
                text,
            ):
                return code

        return None

    def _requires_jurisdiction(
        self,
        text: str,
        intent: LegalIntent,
        domain: LegalDomain,
    ) -> bool:
        # Never block an emergency response simply
        # because the state is unknown.
        if intent == LegalIntent.EMERGENCY:
            return False

        # These intents normally need a location because
        # the responsible authority/service can vary.
        if intent in {
            LegalIntent.AUTHORITY_LOOKUP,
            LegalIntent.COMPLAINT_GUIDANCE,
            LegalIntent.GENERAL_CIVIC,
        }:
            return True

        # Generic legal information can normally proceed
        # without a state, especially for central laws.
        if intent == LegalIntent.LEGAL_INFORMATION:
            return False

        # Evidence/document guidance can normally proceed
        # without jurisdiction.
        if intent == LegalIntent.DOCUMENT_GUIDANCE:
            return False

        # Procedures may require jurisdiction when the query
        # contains clear local/state-specific signals.
        if intent == LegalIntent.LEGAL_PROCEDURE:
            return self._contains_any(
                text,
                self.JURISDICTION_HINT_KEYWORDS,
            )

        return False

    @classmethod
    def _canonical_retrieval_query(
        cls,
        text: str,
        domain: LegalDomain,
    ) -> str | None:
        """
        Build a concise canonical retrieval query for
        recognised criminal-law concepts.

        This normalizes user wording only. It does not
        select or hardcode any statutory provision.
        """
        if domain != LegalDomain.CRIMINAL:
            return None

        matched_concept = None
        matched_alias = None

        for canonical, aliases in cls.RETRIEVAL_CONCEPT_ALIASES.items():
            for alias in aliases:
                pattern = rf"\b{re.escape(alias)}\b"
                if re.search(pattern, text):
                    matched_concept = canonical
                    matched_alias = alias
                    break

            if matched_concept is not None:
                break

        if matched_concept is None or matched_alias is None:
            return None

        if (
            matched_concept == "assault or criminal force"
            and re.search(
                r"\b(?:without\s+(?:any\s+)?provocation|"
                r"no\s+provocation)\b",
                text,
            )
        ):
            return (
                "assault or criminal force otherwise than on "
                "grave and sudden provocation"
            )

        has_penalty_intent = any(
            hint in text
            for hint in cls.PENALTY_QUERY_HINTS
        )

        if has_penalty_intent:
            return f"punishment for {matched_concept}"

        has_definition_intent = any(
            hint in text
            for hint in cls.DEFINITION_QUERY_HINTS
        )

        if has_definition_intent:
            alias = re.escape(matched_alias)
            legal_context = (
                r"(?:\s+(?:under|in)\s+(?:the\s+)?"
                r"(?:bharatiya nyaya sanhita|bns|"
                r"indian(?: criminal)? law))?"
            )
            ending = r"[?.!]?"
            generic_patterns = (
                rf"what is (?:the )?{alias}{legal_context}{ending}",
                rf"what is (?:the )?(?:definition|meaning) "
                rf"of {alias}{legal_context}{ending}",
                rf"(?:define|explain) (?:the )?"
                rf"{alias}{legal_context}{ending}",
                rf"what does (?:the )?{alias} mean"
                rf"{legal_context}{ending}",
                rf"(?:definition|meaning) of (?:the )?"
                rf"{alias}{legal_context}{ending}",
            )

            if any(
                re.fullmatch(pattern, text)
                for pattern in generic_patterns
            ):
                return matched_concept

        return None

    def _rewrite_query(
        self,
        text: str,
        domain: LegalDomain,
        keywords: list[str],
    ) -> list[str]:
        queries = []

        canonical_query = self._canonical_retrieval_query(
            text=text,
            domain=domain,
        )

        if canonical_query is not None:
            queries.append(canonical_query)

        # Preserve the user's normalized wording.
        # This remains available as a fallback/contextual
        # representation even when a canonical query exists.
        queries.append(text)

        if domain == LegalDomain.CRIMINAL:
            queries.append(
                f"Indian criminal law {' '.join(keywords[:8])}"
            )

        elif domain == LegalDomain.PROPERTY:
            queries.append(
                f"Indian property law {' '.join(keywords[:8])}"
            )

        elif domain == LegalDomain.EMPLOYMENT:
            queries.append(
                f"Indian employment law {' '.join(keywords[:8])}"
            )

        elif domain == LegalDomain.CYBERCRIME:
            queries.append(
                f"Indian cybercrime law {' '.join(keywords[:8])}"
            )

        elif domain == LegalDomain.CONSUMER:
            queries.append(
                f"Indian consumer law {' '.join(keywords[:8])}"
            )

        elif domain == LegalDomain.TRAFFIC:
            queries.append(
                f"Indian motor vehicle law {' '.join(keywords[:8])}"
            )

        return list(
            dict.fromkeys(
                query.strip()
                for query in queries
                if query.strip()
            )
        )

    def analyze(
        self,
        query: str,
    ) -> QueryAnalysis:
        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        normalized = self._normalize(query)

        urgency = self._detect_urgency(
            normalized
        )

        intent = self._detect_intent(
            normalized,
            urgency,
        )

        domain = self._detect_domain(
            normalized
        )

        jurisdiction = self._detect_jurisdiction(
            normalized
        )

        keywords = self._extract_keywords(
            normalized
        )

        rewritten_queries = self._rewrite_query(
            normalized,
            domain,
            keywords,
        )

        requires_follow_up = (
            jurisdiction is None
            and self._requires_jurisdiction(
                normalized,
                intent,
                domain,
            )
        )

        missing_information = []

        if requires_follow_up:
            missing_information.append(
                "state_or_jurisdiction"
            )

        return QueryAnalysis(
            original_query=query,
            intent=intent,
            domain=domain,
            jurisdiction=jurisdiction,
            urgency=urgency,
            keywords=keywords,
            rewritten_queries=rewritten_queries,
            requires_follow_up=requires_follow_up,
            missing_information=missing_information,
        )


def get_query_analyzer() -> QueryAnalyzer:
    return QueryAnalyzer()
