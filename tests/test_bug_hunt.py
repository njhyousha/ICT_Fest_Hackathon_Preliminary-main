from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _future(hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(
        minute=0, second=0, microsecond=0
    ).isoformat()


def _fmt(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc).isoformat()


def register_and_login(org_name: str, username: str, password: str = "pw12345"):
    reg = client.post(
        "/auth/register",
        json={"org_name": org_name, "username": username, "password": password},
    )
    assert reg.status_code == 201
    login = client.post(
        "/auth/login",
        json={"org_name": org_name, "username": username, "password": password},
    )
    assert login.status_code == 200
    return login.json()["access_token"], login.json()["refresh_token"]


def create_room(token: str):
    response = client.post(
        "/rooms",
        json={"name": "Focus Room", "capacity": 4, "hourly_rate_cents": 1000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_booking(token: str, room_id: int, start: str, end: str):
    return client.post(
        "/bookings",
        json={"room_id": room_id, "start_time": start, "end_time": end},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_booking_start_time_must_be_strictly_in_future():
    org = f"org-{uuid4().hex}"
    token, _ = register_and_login(org, "alice")
    room_id = create_room(token)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    start = _fmt(now)
    end = _fmt(now + timedelta(hours=1))

    booking = create_booking(token, room_id, start, end)
    assert booking.status_code == 400
    assert booking.json()["code"] == "INVALID_BOOKING_WINDOW"


def test_booking_zero_duration_is_rejected():
    org = f"org-{uuid4().hex}"
    token, _ = register_and_login(org, "bob")
    room_id = create_room(token)
    start = _future(2)
    end = start

    booking = create_booking(token, room_id, start, end)
    assert booking.status_code == 400
    assert booking.json()["code"] == "INVALID_BOOKING_WINDOW"


def test_back_to_back_bookings_are_allowed():
    org = f"org-{uuid4().hex}"
    token, _ = register_and_login(org, "carol")
    room_id = create_room(token)
    start1 = _future(10)
    end1 = _fmt(datetime.fromisoformat(start1) + timedelta(hours=1))
    start2 = end1
    end2 = _fmt(datetime.fromisoformat(start2) + timedelta(hours=1))

    booking1 = create_booking(token, room_id, start1, end1)
    assert booking1.status_code == 201
    booking2 = create_booking(token, room_id, start2, end2)
    assert booking2.status_code == 201


def test_concurrent_room_conflict_is_resolved():
    org = f"org-{uuid4().hex}"
    token, _ = register_and_login(org, "cathy")
    room_id = create_room(token)
    start = _future(10)
    end = _fmt(datetime.fromisoformat(start) + timedelta(hours=1))

    def attempt():
        return create_booking(token, room_id, start, end)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(attempt) for _ in range(2)]
        results = [future.result() for future in as_completed(futures)]

    statuses = [res.status_code for res in results]
    assert statuses.count(201) == 1
    assert statuses.count(409) == 1


def test_bookings_listed_in_ascending_order():
    org = f"org-{uuid4().hex}"
    token, _ = register_and_login(org, "dave")
    room_id = create_room(token)
    start_a = _future(20)
    start_b = _future(24)
    booking_a = create_booking(token, room_id, start_a, _fmt(datetime.fromisoformat(start_a) + timedelta(hours=1)))
    booking_b = create_booking(token, room_id, start_b, _fmt(datetime.fromisoformat(start_b) + timedelta(hours=1)))
    assert booking_a.status_code == 201
    assert booking_b.status_code == 201

    listing = client.get(
        "/bookings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert items[0]["start_time"] <= items[1]["start_time"]


def test_availability_only_includes_bookings_starting_on_date():
    org = f"org-{uuid4().hex}"
    token, _ = register_and_login(org, "eva")
    room_id = create_room(token)
    date = (datetime.now(timezone.utc) + timedelta(days=1)).date()
    prior_start = datetime.combine(date - timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc) + timedelta(hours=23)
    prior_end = prior_start + timedelta(hours=2)
    future_start = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc) + timedelta(hours=9)
    future_end = future_start + timedelta(hours=1)

    booking1 = create_booking(token, room_id, _fmt(prior_start), _fmt(prior_end))
    assert booking1.status_code == 201
    booking2 = create_booking(token, room_id, _fmt(future_start), _fmt(future_end))
    assert booking2.status_code == 201

    avail = client.get(
        f"/rooms/{room_id}/availability",
        params={"date": date.isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert avail.status_code == 200
    busy = avail.json()["busy"]
    assert len(busy) == 1
    assert busy[0]["start_time"] == _fmt(future_start)


def test_refund_rounding_uses_half_up_and_single_refund_row():
    org = f"org-{uuid4().hex}"
    token, _ = register_and_login(org, "frank")
    response = client.post(
        "/rooms",
        json={"name": "Focus Room", "capacity": 4, "hourly_rate_cents": 1001},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    room_id = response.json()["id"]
    start = _future(25)
    end = _fmt(datetime.fromisoformat(start) + timedelta(hours=1))
    booking = create_booking(token, room_id, start, end)
    assert booking.status_code == 201
    booking_id = booking.json()["id"]

    cancel = client.post(
        f"/bookings/{booking_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cancel.status_code == 200
    assert cancel.json()["refund_percent"] == 50
    assert cancel.json()["refund_amount_cents"] == 501

    detail = client.get(
        f"/bookings/{booking_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.status_code == 200
    refunds = detail.json().get("refunds", [])
    assert len(refunds) == 1
    assert refunds[0]["amount_cents"] == 501


def test_concurrent_cancellations_only_refund_once():
    org = f"org-{uuid4().hex}"
    token, _ = register_and_login(org, "gina")
    room_id = create_room(token)
    start = _future(25)
    end = _fmt(datetime.fromisoformat(start) + timedelta(hours=1))
    booking = create_booking(token, room_id, start, end)
    assert booking.status_code == 201
    booking_id = booking.json()["id"]

    def attempt_cancel():
        return client.post(
            f"/bookings/{booking_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(attempt_cancel) for _ in range(2)]
        results = [future.result() for future in as_completed(futures)]

    statuses = [res.status_code for res in results]
    assert statuses.count(200) == 1
    assert statuses.count(409) == 1


def test_refresh_token_is_single_use():
    org = f"org-{uuid4().hex}"
    token, refresh_token = register_and_login(org, "gary")
    first = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert first.status_code == 200
    second = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert second.status_code == 401


def test_quota_is_enforced_under_concurrent_requests():
    org = f"org-{uuid4().hex}"
    token, _ = register_and_login(org, "helen")
    room_id = create_room(token)
    base = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=1)
    starts = [base + timedelta(hours=i * 2) for i in range(3)]
    for start in starts:
        resp = create_booking(token, room_id, _fmt(start), _fmt(start + timedelta(hours=1)))
        assert resp.status_code == 201

    request_slots = [base + timedelta(hours=4), base + timedelta(hours=5)]

    def attempt(start_time):
        return create_booking(token, room_id, _fmt(start_time), _fmt(start_time + timedelta(hours=1)))

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(attempt, slot) for slot in request_slots]
        results = [future.result() for future in as_completed(futures)]

    statuses = [res.status_code for res in results]
    assert statuses.count(201) + statuses.count(409) == 2
    assert statuses.count(201) == 0 or statuses.count(409) == 2


def test_room_stats_tracks_concurrent_bookings():
    org = f"org-{uuid4().hex}"
    token, _ = register_and_login(org, "irene")
    room_id = create_room(token)
    base = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=10)
    slots = [base + timedelta(hours=i * 2) for i in range(2)]

    def attempt(start_time):
        return create_booking(token, room_id, _fmt(start_time), _fmt(start_time + timedelta(hours=1)))

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(attempt, slot) for slot in slots]
        results = [future.result() for future in as_completed(futures)]

    assert all(res.status_code == 201 for res in results)

    stats = client.get(
        f"/rooms/{room_id}/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert stats.status_code == 200
    assert stats.json()["total_confirmed_bookings"] == 2
