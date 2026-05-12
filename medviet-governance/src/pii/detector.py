from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider


def build_vietnamese_analyzer() -> AnalyzerEngine:
    """Build an AnalyzerEngine with Vietnamese-specific recognizers."""
    cccd_recognizer = PatternRecognizer(
        supported_entity="VN_CCCD",
        supported_language="vi",
        patterns=[Pattern(
            name="cccd_pattern",
            regex=r"(?<!\d)\d{12}(?!\d)",
            score=0.9,
        )],
        context=["cccd", "can cuoc", "chung minh", "cmnd"],
    )

    phone_recognizer = PatternRecognizer(
        supported_entity="VN_PHONE",
        supported_language="vi",
        patterns=[Pattern(
            name="vn_phone",
            regex=r"(?<!\d)0[35789]\d{8}(?!\d)",
            score=0.85,
        )],
        context=["dien thoai", "sdt", "phone", "lien he"],
    )

    email_recognizer = PatternRecognizer(
        supported_entity="EMAIL_ADDRESS",
        supported_language="vi",
        patterns=[Pattern(
            name="email",
            regex=r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
            score=0.85,
        )],
        context=["email", "mail"],
    )

    # The lab's vi_core_news_lg package has no NER pipe, so names need a
    # pattern fallback. The regex module supports Unicode property classes.
    name_word = r"(?:\p{Lu}[\p{Ll}\p{Mn}]+|\p{Lu})"
    person_recognizer = PatternRecognizer(
        supported_entity="PERSON",
        supported_language="vi",
        patterns=[Pattern(
            name="vn_person_name",
            regex=rf"(?<![\p{{L}}]){name_word}(?:\s+{name_word}){{1,4}}(?![\p{{L}}])",
            score=0.65,
        )],
        context=["benh nhan", "ho ten", "bac si"],
    )

    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "vi", "model_name": "vi_core_news_lg"}],
    })
    nlp_engine = provider.create_engine()

    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["vi"])
    analyzer.registry.add_recognizer(cccd_recognizer)
    analyzer.registry.add_recognizer(phone_recognizer)
    analyzer.registry.add_recognizer(email_recognizer)
    analyzer.registry.add_recognizer(person_recognizer)

    return analyzer


def detect_pii(text: str, analyzer: AnalyzerEngine) -> list:
    """Detect supported PII entities in Vietnamese text."""
    return analyzer.analyze(
        text=str(text),
        language="vi",
        entities=["PERSON", "EMAIL_ADDRESS", "VN_CCCD", "VN_PHONE"],
    )
