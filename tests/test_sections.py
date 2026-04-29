from wikifi.sections import (
    DERIVATIVE_SECTION_IDS,
    DERIVATIVE_SECTIONS,
    PRIMARY_SECTION_IDS,
    PRIMARY_SECTIONS,
    SECTION_IDS,
    SECTIONS,
    SECTIONS_BY_ID,
)


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


def test_primary_and_derivative_partitions_cover_every_section():
    assert set(PRIMARY_SECTION_IDS) | set(DERIVATIVE_SECTION_IDS) == set(SECTION_IDS)
    assert set(PRIMARY_SECTION_IDS) & set(DERIVATIVE_SECTION_IDS) == set()


def test_primary_sections_have_no_upstream():
    for section in PRIMARY_SECTIONS:
        assert section.derived_from == ()
        assert section.tier == "primary"


def test_derivative_sections_declare_upstreams_that_resolve():
    assert DERIVATIVE_SECTION_IDS, "expected at least one derivative section"
    for section in DERIVATIVE_SECTIONS:
        assert section.derived_from, f"{section.id} must declare derived_from"
        for upstream_id in section.derived_from:
            assert upstream_id in SECTIONS_BY_ID, f"{section.id} -> unknown upstream {upstream_id}"


def test_derivative_upstreams_appear_earlier_in_sections_tuple():
    """Derivation order in run_walk follows SECTIONS order — upstreams must precede dependents."""
    seen: set[str] = set()
    for section in SECTIONS:
        for upstream_id in section.derived_from:
            assert upstream_id in seen, f"{section.id} depends on {upstream_id}, which appears later in SECTIONS"
        seen.add(section.id)


def test_personas_user_stories_diagrams_are_derivative():
    """Lock the user-facing tier choice for the canonical derivatives."""
    for sid in ("personas", "user_stories", "diagrams"):
        assert SECTIONS_BY_ID[sid].tier == "derivative", f"{sid} must be derivative"
