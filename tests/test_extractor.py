from datetime import date

from app import extractor
from app.sample import SAMPLES

REF = date(2026, 10, 28)


def by_title(cards, fragment):
    return next(c for c in cards if fragment.lower() in c.title.lower())


def test_sample_extracts_all_cards():
    result = extractor.extract(SAMPLES["en"], REF)
    assert len(result["cards"]) == 9
    assert len(result["decisions"]) == 2
    assert len(result["risks"]) == 2
    assert len(result["questions"]) == 1


def test_owner_due_and_labels():
    cards = extractor.extract(SAMPLES["en"], REF)["cards"]
    card = by_title(cards, "onboarding mockups")
    assert card.owner == "Anna"
    assert card.due == "2026-10-30"
    assert "design" in card.labels


def test_status_columns():
    cards = extractor.extract(SAMPLES["en"], REF)["cards"]
    assert by_title(cards, "staging").column == "done"
    assert by_title(cards, "payment module").column == "review"
    assert by_title(cards, "login bug").column == "todo"


def test_priority_and_kind():
    cards = extractor.extract(SAMPLES["en"], REF)["cards"]
    bug = by_title(cards, "login bug")
    assert bug.priority == "critical"
    assert bug.kind == "bug"
    assert bug.moscow == "Must"
    assert by_title(cards, "competitor").priority == "low"


def test_explicit_points_and_iso_date():
    card = by_title(extractor.extract(SAMPLES["en"], REF)["cards"], "billing")
    assert card.points == 8
    assert card.due == "2026-11-12"


def test_blocked_label():
    card = by_title(extractor.extract(SAMPLES["en"], REF)["cards"], "analytics dashboard")
    assert "blocked" in card.labels


def test_polish_notes():
    result = extractor.extract(SAMPLES["pl"], REF)
    assert len(result["cards"]) == 9
    makiety = by_title(result["cards"], "makiety")
    assert makiety.owner == "Anna"
    assert makiety.due == "2026-10-30"
    assert by_title(result["cards"], "staging").column == "done"
    assert by_title(result["cards"], "błąd logowania").priority == "critical"
    assert result["questions"]


def test_free_text_without_sections():
    notes = "Kasia will draft the contract by 5.11\nJan: update the roadmap tomorrow"
    cards = extractor.extract(notes, REF)["cards"]
    assert [c.owner for c in cards] == ["Kasia", "Jan"]
    assert cards[0].due == "2026-11-05"
    assert cards[1].due == "2026-10-29"


def test_ignores_chatter():
    notes = "We talked about the weather and lunch.\nGood energy in the room."
    assert extractor.extract(notes, REF)["cards"] == []


def test_deduplicates():
    notes = "Action items:\n- Anna: send report\n- Anna: send report"
    assert len(extractor.extract(notes, REF)["cards"]) == 1


def test_informal_polish_without_diacritics():
    notes = (
        "Natalia ma zrobic 3 pojkty alan 8 i ma dodac wtyczki a klaudia przysoady\n"
        "w progresie maciekj juz robi ayutio\n"
        "\n"
        "maciek juz robi auto"
    )
    cards = extractor.extract(notes, REF)["cards"]
    assert [(c.owner, c.column) for c in cards] == [
        ("Natalia", "todo"),
        ("Natalia", "todo"),
        ("Klaudia", "todo"),
        ("Maciekj", "doing"),
        ("Maciek", "doing"),
    ]
    assert cards[1].title == "Dodac wtyczki"
    assert cards[2].title == "Przysoady"


def test_english_pronouns_are_not_owners():
    cards = extractor.extract("We will ship the release on Friday", REF)["cards"]
    assert all(c.owner is None for c in cards)
