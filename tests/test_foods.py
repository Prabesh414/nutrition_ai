"""Food catalogue search."""
import pytest

API = "/api/v1"


def test_search_is_public(client):
    """The catalogue is reference data, not user data."""
    assert client.get(f"{API}/foods?query=oat").status_code == 200


def test_search_matches_a_name_fragment(client):
    results = client.get(f"{API}/foods?query=soymilk").json()
    assert results
    assert all("soymilk" in item["name"].lower() for item in results)


def test_search_is_case_insensitive(client):
    lower = client.get(f"{API}/foods?query=soymilk").json()
    upper = client.get(f"{API}/foods?query=SOYMILK").json()
    assert [item["id"] for item in lower] == [item["id"] for item in upper]


def test_results_carry_the_full_nutrition_payload(client):
    item = client.get(f"{API}/foods?query=soymilk").json()[0]
    for field in ("id", "name", "serving_size", "region", "calories", "fat",
                  "carbohydrates", "protein", "fiber", "sugars",
                  "is_vegetarian", "is_vegan"):
        assert field in item, field


def test_empty_query_returns_a_sample(client):
    assert len(client.get(f"{API}/foods").json()) > 0


def test_no_match_returns_an_empty_list(client):
    assert client.get(f"{API}/foods?query=zzzznotafood").json() == []


@pytest.mark.parametrize("wildcard", ["%", "_", "%%", "a%b", "\\"])
def test_like_wildcards_in_user_input_are_escaped(client, wildcard):
    """A bare '%' must be a literal, not a match-everything wildcard."""
    results = client.get(f"{API}/foods?query={wildcard}").json()
    assert results == [], f"{wildcard!r} behaved as a wildcard"


def test_dietary_filters(client):
    vegan = client.get(f"{API}/foods?query=a&vegan=true&limit=50").json()
    assert vegan
    assert all(item["is_vegan"] for item in vegan)

    vegetarian = client.get(f"{API}/foods?query=a&vegetarian=true&limit=50").json()
    assert all(item["is_vegetarian"] for item in vegetarian)


def test_limit_is_respected_and_bounded(client):
    assert len(client.get(f"{API}/foods?limit=5").json()) <= 5
    assert client.get(f"{API}/foods?limit=0").status_code == 422
    assert client.get(f"{API}/foods?limit=500").status_code == 422


def test_overlong_query_is_rejected(client):
    assert client.get(f"{API}/foods?query={'x' * 200}").status_code == 422


def test_results_are_alphabetical(client):
    names = [item["name"] for item in client.get(f"{API}/foods?query=soy&limit=30").json()]
    assert names == sorted(names)
