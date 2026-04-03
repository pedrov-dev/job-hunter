from src.companies import COMPANIES, COMPANY_GROUPS, GROUP_SLUGS, build_company_list


def test_company_groups_follow_master_company_order():
    expected = {
        group_name: [company for company in COMPANIES if company[0] in GROUP_SLUGS[group_name]]
        for group_name in GROUP_SLUGS
    }

    assert COMPANY_GROUPS == expected


def test_build_company_list_deduplicates_overlapping_groups_in_order():
    selected = build_company_list(["latam_remote", "global_remote_friendly"])
    slugs = [slug for slug, _ in selected]

    assert len(slugs) == len(set(slugs))
    assert slugs[:6] == [
        "factored",
        "arionkoder",
        "xebia",
        "quora",
        "cohere",
        "handshake",
    ]
    assert slugs[-8:] == [
        "intercom",
        "typeform",
        "zapier",
        "zendesk",
        "brex",
        "ramp",
        "mercury",
        "leapsome",
    ]
