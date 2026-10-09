from dataclasses import dataclass


@dataclass(frozen=True)
class MoldedRetrievalExample:
    case_id: str
    category: str
    query: str
    expected_act_short_name: str
    expected_section_numbers: tuple[str, ...]


MOLDED_RETRIEVAL_DATASET = [
    MoldedRetrievalExample(
        case_id="BNS-M01",
        category="colloquial_multi_part",
        query=(
            "What is the provision for mob lynching under the BNS, "
            "and what is the punishment?"
        ),
        expected_act_short_name="BNS",
        expected_section_numbers=("103",),
    ),
    MoldedRetrievalExample(
        case_id="BNS-M02",
        category="scenario",
        query=(
            "Five or more people acting together kill a person because "
            "of that person's caste. What BNS rule covers this?"
        ),
        expected_act_short_name="BNS",
        expected_section_numbers=("103",),
    ),
    MoldedRetrievalExample(
        case_id="BNS-M03",
        category="statutory_concept",
        query="How does the BNS define a terrorist act?",
        expected_act_short_name="BNS",
        expected_section_numbers=("113",),
    ),
    MoldedRetrievalExample(
        case_id="BNS-M04",
        category="plain_language_scenario",
        query=(
            "A rider suddenly grabbed a phone from someone's hand and "
            "sped away. Which BNS offence describes this?"
        ),
        expected_act_short_name="BNS",
        expected_section_numbers=("304",),
    ),
    MoldedRetrievalExample(
        case_id="BNS-M05",
        category="element_based_scenario",
        query=(
            "Someone dishonestly moved another person's movable property "
            "without consent in order to take it. What offence is this?"
        ),
        expected_act_short_name="BNS",
        expected_section_numbers=("303",),
    ),
    MoldedRetrievalExample(
        case_id="BNS-M06",
        category="definition",
        query=(
            "When does theft become robbery under the Bharatiya Nyaya "
            "Sanhita?"
        ),
        expected_act_short_name="BNS",
        expected_section_numbers=("309",),
    ),
    MoldedRetrievalExample(
        case_id="BNS-M07",
        category="threat_scenario_non_emergency",
        query=(
            "I am safe now, but someone threatened injury to frighten me "
            "into doing something. Which BNS offence may be relevant?"
        ),
        expected_act_short_name="BNS",
        expected_section_numbers=("351",),
    ),
    MoldedRetrievalExample(
        case_id="BNS-M08",
        category="qualifier_sensitive_scenario",
        query=(
            "A person intentionally hit me without any provocation. I am "
            "safe now. Which BNS provision may apply?"
        ),
        expected_act_short_name="BNS",
        expected_section_numbers=("131",),
    ),
    MoldedRetrievalExample(
        case_id="BNS-M09",
        category="plain_language_scenario",
        query=(
            "A person deceived someone and dishonestly induced them to "
            "deliver money. What BNS offence covers that conduct?"
        ),
        expected_act_short_name="BNS",
        expected_section_numbers=("318",),
    ),
    MoldedRetrievalExample(
        case_id="BNS-M10",
        category="plain_language_scenario",
        query=(
            "Property was entrusted to a person, but that person "
            "dishonestly misappropriated it. Which BNS offence applies?"
        ),
        expected_act_short_name="BNS",
        expected_section_numbers=("316",),
    ),
    MoldedRetrievalExample(
        case_id="BNS-M11",
        category="complex_definition",
        query=(
            "What does the BNS call continuing unlawful activity by an "
            "organised crime syndicate using violence or coercion for "
            "material benefit?"
        ),
        expected_act_short_name="BNS",
        expected_section_numbers=("111",),
    ),
    MoldedRetrievalExample(
        case_id="BNS-M12",
        category="multi_part",
        query=(
            "What is petty organised crime under the BNS and what is its "
            "punishment?"
        ),
        expected_act_short_name="BNS",
        expected_section_numbers=("112",),
    ),
    MoldedRetrievalExample(
        case_id="COI-M01",
        category="constitutional_scenario",
        query=(
            "Which constitutional protection says that a person cannot "
            "be deprived of life or personal liberty except according to "
            "procedure established by law?"
        ),
        expected_act_short_name="COI",
        expected_section_numbers=("21",),
    ),
    MoldedRetrievalExample(
        case_id="COI-M02",
        category="constitutional_plain_language",
        query=(
            "Where does the Constitution guarantee equality before the "
            "law and equal protection of the laws?"
        ),
        expected_act_short_name="COI",
        expected_section_numbers=("14",),
    ),
    MoldedRetrievalExample(
        case_id="COI-M03",
        category="constitutional_multi_part",
        query=(
            "Which Article protects freedom of speech and expression, "
            "and does the constitutional text also permit restrictions?"
        ),
        expected_act_short_name="COI",
        expected_section_numbers=("19",),
    ),
    MoldedRetrievalExample(
        case_id="COI-M04",
        category="constitutional_scenario",
        query=(
            "What constitutional provision concerns free and compulsory "
            "education for children from six to fourteen years?"
        ),
        expected_act_short_name="COI",
        expected_section_numbers=("21A",),
    ),
    MoldedRetrievalExample(
        case_id="COI-M05",
        category="constitutional_plain_language",
        query="Which constitutional Article abolishes untouchability?",
        expected_act_short_name="COI",
        expected_section_numbers=("17",),
    ),
    MoldedRetrievalExample(
        case_id="COI-M06",
        category="constitutional_remedy",
        query=(
            "Which constitutional provision guarantees the right to move "
            "the Supreme Court to enforce fundamental rights?"
        ),
        expected_act_short_name="COI",
        expected_section_numbers=("32",),
    ),
    MoldedRetrievalExample(
        case_id="COI-M07",
        category="constitutional_qualifiers",
        query=(
            "Where does the Constitution prohibit discrimination on "
            "grounds only of religion, race, caste, sex or place of birth?"
        ),
        expected_act_short_name="COI",
        expected_section_numbers=("15",),
    ),
    MoldedRetrievalExample(
        case_id="COI-M08",
        category="constitutional_plain_language",
        query=(
            "Which constitutional provision prohibits trafficking in "
            "human beings, begar and similar forced labour?"
        ),
        expected_act_short_name="COI",
        expected_section_numbers=("23",),
    ),
]
