from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence
from app.services.claim_validator import LegalClaimValidator as V


def valid(statement, source):
    items = [LegalEvidence(citation_id='E1', chunk_id=1, content=source)]
    return V.validate(answer=LegalAnswer(summary=statement, citations=['E1']), evidence=items).is_valid


MANDATORY = (
    'If a person is convicted for the first time and returns the stolen property, '
    'he shall be punished with community service.'
)
PREFIX = 'If a person is convicted for the first time and returns the stolen property, '


def test_softening_is_rejected():
    assert not valid(PREFIX + 'the punishment may include community service.', MANDATORY)


def test_correct_mandatory_paraphrase_passes():
    assert valid(PREFIX + 'the punishment is community service.', MANDATORY)


def test_discretionary_source_stays_discretionary():
    source = MANDATORY.replace('shall be', 'may be')
    assert valid(PREFIX + 'the punishment may include community service.', source)


def test_source_alternatives_do_not_make_one_option_mandatory():
    source = MANDATORY.replace('community service.', 'community service or a fine.')
    assert valid(PREFIX + 'the punishment may include community service.', source)


def test_may_extend_remains_valid():
    source = ('If a person assaults another while attempting theft, he shall be '
              'punished with imprisonment for a term which may extend to two years.')
    assert valid(source, source)


def test_wrong_maximum_is_rejected():
    source = ('If a person assaults another while attempting theft, he shall be '
              'punished with imprisonment for a term which may extend to two years.')
    assert not valid(source.replace('two years', 'ten years'), source)


def test_digit_and_word_maximum_are_equivalent():
    source = ('If a person assaults another while attempting theft, he shall be '
              'punished with imprisonment for a term which may extend to two years.')
    assert valid(source.replace('two years', '2 years'), source)


def test_multiple_alternative_conditions_with_same_penalty_pass():
    source = ('If a person assaults another, he shall be punished with imprisonment '
              'up to two years. If a person damages property, he shall be punished '
              'with imprisonment up to two years.')
    claim = ('If a person assaults another, or if a person damages property, '
             'the punishment is imprisonment up to two years.')
    assert valid(claim, source)


def test_multiple_alternative_conditions_with_different_penalties_fail():
    source = ('If a person assaults another, he shall be punished with imprisonment '
              'up to two years. If a person damages property, he shall be punished '
              'with imprisonment up to ten years.')
    claim = ('If a person assaults another, or if a person damages property, '
             'the punishment is imprisonment up to ten years.')
    assert not valid(claim, source)


def test_discretionary_source_does_not_license_a_different_mandatory_rule():
    source = (MANDATORY + ' If a person damages property, he may be punished '
              'with community service.')
    assert not valid(PREFIX + 'the punishment may include community service.', source)


def test_equivalent_years_and_months_pass():
    source = ('If a person assaults another while attempting theft, he shall be '
              'punished with imprisonment for a term which may extend to two years.')
    assert valid(source.replace('two years', '24 months'), source)


def test_different_maximum_in_months_fails():
    source = ('If a person assaults another while attempting theft, he shall be '
              'punished with imprisonment for a term which may extend to two years.')
    assert not valid(source.replace('two years', '20 months'), source)
