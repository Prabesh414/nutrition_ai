from backend.main import ProfileCreateRequest


def test_profile_request_accepts_profile_image_url():
    payload = ProfileCreateRequest(
        email='user@example.com',
        profile_image_url='data:image/png;base64,abc123'
    )

    assert payload.profile_image_url == 'data:image/png;base64,abc123'
