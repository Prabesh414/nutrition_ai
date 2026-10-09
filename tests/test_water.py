"""Tests for water intake tracking and summary calculations."""
from datetime import date, timedelta


def test_water_logging_and_summary(client, register_user):
    headers, user = register_user()
    today = date.today().isoformat()

    # Initial summary
    res = client.get(f"/api/v1/water/summary?log_date={today}", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total_ml"] == 0.0
    assert body["target_ml"] == 2500.0  # default without profile
    assert body["progress_pct"] == 0.0
    assert body["logs"] == []

    # Log 250ml
    res_add1 = client.post("/api/v1/water", json={"amount_ml": 250.0, "log_date": today}, headers=headers)
    assert res_add1.status_code == 201
    log1 = res_add1.json()
    assert log1["amount_ml"] == 250.0

    # Log 500ml
    res_add2 = client.post("/api/v1/water", json={"amount_ml": 500.0, "log_date": today}, headers=headers)
    assert res_add2.status_code == 201
    log2 = res_add2.json()

    # Check updated summary
    res_summary = client.get(f"/api/v1/water/summary?log_date={today}", headers=headers)
    assert res_summary.status_code == 200
    summary_data = res_summary.json()
    assert summary_data["total_ml"] == 750.0
    assert summary_data["progress_pct"] == 30.0  # (750 / 2500) * 100
    assert len(summary_data["logs"]) == 2

    # Delete one entry
    res_del = client.delete(f"/api/v1/water/{log1['id']}", headers=headers)
    assert res_del.status_code == 204

    # Verify summary after delete
    res_after_del = client.get(f"/api/v1/water/summary?log_date={today}", headers=headers)
    assert res_after_del.status_code == 200
    assert res_after_del.json()["total_ml"] == 500.0

    # Reset day's water
    res_reset = client.delete(f"/api/v1/water/reset/day?log_date={today}", headers=headers)
    assert res_reset.status_code == 204

    res_after_reset = client.get(f"/api/v1/water/summary?log_date={today}", headers=headers)
    assert res_after_reset.status_code == 200
    assert res_after_reset.json()["total_ml"] == 0.0


def test_water_security_other_user_log_isolation(client, register_user):
    headers1, _ = register_user()
    headers2, _ = register_user()
    today = date.today().isoformat()

    # User 1 logs water
    res_add = client.post("/api/v1/water", json={"amount_ml": 500.0, "log_date": today}, headers=headers1)
    assert res_add.status_code == 201
    log1_id = res_add.json()["id"]

    # User 2 cannot see or delete User 1's water log
    res_u2_summary = client.get(f"/api/v1/water/summary?log_date={today}", headers=headers2)
    assert res_u2_summary.status_code == 200
    assert res_u2_summary.json()["total_ml"] == 0.0

    res_del_attack = client.delete(f"/api/v1/water/{log1_id}", headers=headers2)
    assert res_del_attack.status_code == 404
