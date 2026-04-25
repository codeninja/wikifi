from wikifi.sections import SECTION_IDS, SECTIONS, SECTIONS_BY_ID


def test_section_ids_are_unique():
    assert len(SECTION_IDS) == len(set(SECTION_IDS))


def test_every_section_has_title_and_description():
    for section in SECTIONS:
        assert section.title.strip()
        assert section.description.strip()


def test_sections_by_id_round_trip():
    for section in SECTIONS:
        assert SECTIONS_BY_ID[section.id] is section


def test_section_ids_are_valid_filenames():
    for sid in SECTION_IDS:
        assert sid.replace("_", "").isalnum(), sid
