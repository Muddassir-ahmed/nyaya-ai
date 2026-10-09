from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text_matching import contains_any
from app.schemas.authority import AuthorityResponse
from app.schemas.query_analysis import (
    LegalDomain,
    QueryAnalysis,
)
from app.services.authority_service import AuthorityService
from app.services.query_analyzer import (
    QueryAnalyzer,
    get_query_analyzer,
)


class AuthorityOrchestrator:
    """
    Deterministically route authority-lookup queries to a
    verified structured government authority service.

    The LLM is never used to invent:
    - authority names
    - contact numbers
    - URLs
    - complaint portals
    - email addresses
    """

    CYBERCRIME_KEYWORDS = {
        "cybercrime",
        "cyber crime",
        "phishing",
        "online fraud",
        "account hacked",
        "email hacked",
        "instagram hacked",
        "password stolen",
        "otp fraud",
    }

    CONSUMER_KEYWORDS = {
        "consumer",
        "defective product",
        "refund",
        "warranty",
        "seller",
        "consumer complaint",
    }

    LABOUR_KEYWORDS = {
        "salary",
        "unpaid salary",
        "wages",
        "employer",
        "employee",
        "termination",
        "dismissed",
        "workplace",
        "employment",
    }

    DRIVING_LICENCE_KEYWORDS = {
    "driving licence",
    "driving license",
    "learner licence",
    "learner license",
    "learner's licence",
    "learner's license",
    "licence renewal",
    "license renewal",
    "renew driving licence",
    "renew driving license",
}

    VEHICLE_REGISTRATION_KEYWORDS = {
    "vehicle registration",
    "registration certificate",
    "vehicle rc",
    "rc transfer",
    "transfer ownership",
    "vehicle ownership transfer",
}

    TRAFFIC_CHALLAN_KEYWORDS = {
    "challan",
    "traffic challan",
    "e-challan",
    "echallan",
    "incorrect challan",
    "wrong challan",
    "challan grievance",
}

    TRANSPORT_KEYWORDS = {
    "rto",
    "transport department",
    "transport office",
    "motor vehicle department",
}

    PROPERTY_KEYWORDS = {
        "property",
        "land",
        "landlord",
        "tenant",
        "eviction",
        "lease",
        "revenue department",
        "land record",
    }

    POLICE_KEYWORDS = {
        "theft",
        "stolen",
        "robbery",
        "assault",
        "crime",
        "criminal",
        "police",
        "fir",
        "kidnap",
        "rape",
        "trespass",
        "threat",
        "cheating",
    }

    LEGAL_AID_KEYWORDS = {
    "legal aid",
    "free legal aid",
    "free legal services",
    "legal services authority",
    "free lawyer",
    }

    DISTRICT_ADMINISTRATION_KEYWORDS = {
    "district administration",
    "district office",
    "deputy commissioner",
    "dc office",
    "residence certificate",
    "income certificate",
    "domicile certificate",
    }

    def __init__(
        self,
        authority_service: AuthorityService | None = None,
        query_analyzer: QueryAnalyzer | None = None,
    ):
        self.authority_service = (
            authority_service
            or AuthorityService()
        )

        self.query_analyzer = (
            query_analyzer
            or get_query_analyzer()
        )

    @staticmethod
    def _resolve_jurisdiction(
        analysis: QueryAnalysis,
        jurisdiction: str | None,
    ) -> str | None:
        """
        Explicit caller jurisdiction takes precedence over
        jurisdiction detected from the query.

        Analyzer shorthand jurisdiction codes are normalized
        to the canonical codes stored in the jurisdiction table.
        """

        if jurisdiction is not None:
            value = jurisdiction.strip()

            if value:
                return value

        detected = analysis.jurisdiction

        if detected is None:
            return None

        jurisdiction_aliases = {
            "AS": "IN-AS",
            "MH": "IN-MH",
            "KA": "IN-KA",
            "IN": "IN",
        }

        return jurisdiction_aliases.get(
            detected,
            detected,
        )

    @classmethod
    def _detect_service_key(
        cls,
        query: str,
        analysis: QueryAnalysis,
    ) -> str:
        """
        Convert a situation into a stable machine-readable
        authority service key.

        Specific situation keywords take priority over the
        broader domain classification.
        """

        if contains_any(
            query,
            cls.CYBERCRIME_KEYWORDS,
        ):
            return "cybercrime_report"

        if contains_any(
            query,
            cls.CONSUMER_KEYWORDS,
        ):
            return "consumer_grievance"

        if contains_any(
            query,
            cls.LABOUR_KEYWORDS,
        ):
            return "labour_grievance"

        if contains_any(
            query,
            cls.LEGAL_AID_KEYWORDS,
        ):
            return "legal_aid_service"

        if contains_any(
            query,
            cls.DISTRICT_ADMINISTRATION_KEYWORDS,
        ):
            return "district_administration_service"

        if contains_any(
            query,
            cls.DRIVING_LICENCE_KEYWORDS,
       ):
            return "driving_licence_service"

        if contains_any(
            query,
            cls.VEHICLE_REGISTRATION_KEYWORDS,
        ):
            return "vehicle_registration_service"

        if contains_any(
            query,
            cls.TRAFFIC_CHALLAN_KEYWORDS,
        ):
            return "traffic_challan_service"

        if contains_any(
            query,
            cls.TRANSPORT_KEYWORDS,
        ):
            return "transport_service"

        if contains_any(
            query,
            cls.PROPERTY_KEYWORDS,
        ):
            return "property_land_service"

        if contains_any(
            query,
            cls.POLICE_KEYWORDS,
        ):
            return "police_complaint"


        domain_mapping = {
            LegalDomain.CYBERCRIME: "cybercrime_report",
            LegalDomain.CONSUMER: "consumer_grievance",
            LegalDomain.EMPLOYMENT: "labour_grievance",
            LegalDomain.TRAFFIC: "transport_service",
            LegalDomain.PROPERTY: "property_land_service",
            LegalDomain.CRIMINAL: "police_complaint",
        }

        return domain_mapping.get(
            analysis.domain,
            "general_authority",
        )

    async def handle(
        self,
        db: AsyncSession,
        query: str,
        jurisdiction: str | None = None,
        analysis: QueryAnalysis | None = None,
    ) -> AuthorityResponse:
        """
        Resolve the correct authority service for one user
        situation and return only verified database records.
        """

        current_analysis = (
            analysis
            if analysis is not None
            else self.query_analyzer.analyze(query)
        )

        service_key = self._detect_service_key(
            query=query,
            analysis=current_analysis,
        )

        resolved_jurisdiction = (
            self._resolve_jurisdiction(
                analysis=current_analysis,
                jurisdiction=jurisdiction,
            )
        )

        if resolved_jurisdiction is None:
            return AuthorityResponse(
                service_key=service_key,
                jurisdiction=None,
                authorities=[],
                verification_note=(
                    "A jurisdiction is required before NyayaAI "
                    "can select a verified authority."
                ),
            )

        authorities = (
            await self.authority_service
            .get_verified_authorities(
                db=db,
                service_key=service_key,
                jurisdiction=resolved_jurisdiction,
            )
        )

        if not authorities:
            return AuthorityResponse(
                service_key=service_key,
                jurisdiction=resolved_jurisdiction,
                authorities=[],
                verification_note=(
                    "No verified active authority record is "
                    "currently available for this service and "
                    "jurisdiction."
                ),
            )

        return AuthorityResponse(
            service_key=service_key,
            jurisdiction=resolved_jurisdiction,
            authorities=authorities,
            verification_note=(
                "Authority information was retrieved from "
                "verified structured records."
            ),
        )


def get_authority_orchestrator() -> AuthorityOrchestrator:
    return AuthorityOrchestrator()
