from app.schemas.citation import CitationVerification
from app.schemas.legal_evidence import LegalEvidence
from app.services.citation_verifier import verify_legal_evidence


class VerifiedLegalEvidence:
    def __init__(
        self,
        evidence: LegalEvidence,
        verification: CitationVerification,
    ):
        self.evidence = evidence
        self.verification = verification


def verify_evidence_list(
    evidence_list: list[LegalEvidence],
) -> list[VerifiedLegalEvidence]:

    verified_evidence = []

    citation_number = 1

    for evidence in evidence_list:

        verification = verify_legal_evidence(
            evidence
        )

        if not verification.is_valid:
            continue

        evidence.citation_id = (
            f"E{citation_number}"
        )

        citation_number += 1

        verified_evidence.append(
            VerifiedLegalEvidence(
                evidence=evidence,
                verification=verification,
            )
        )

    return verified_evidence