# Bug Report

## Fixed Bugs

1. **Incorrect future start-time validation**
   - Files: `app/routers/bookings.py`
   - Issue: `create_booking` incorrectly allowed `start_time` equal to `now` by checking `start <= now - timedelta(seconds=300)`. This violated rule 2 requiring `start_time` to be strictly in the future with no grace window.
   - Fix: changed validation to `if start <= now`.
   - Difficulty: Easy — simple boundary check.

2. **Missing zero-duration / end-time ordering validation**
   - Files: `app/routers/bookings.py`
   - Issue: `create_booking` allowed `end_time == start_time` and did not reject durations below 1 hour. The duration range check only enforced a maximum, not a minimum, and there was no explicit `end_time > start_time` validation.
   - Fix: added explicit `end <= start` rejection and enforced `duration_hours` between 1 and 8.
   - Difficulty: Easy — booking window validation.

3. **Back-to-back booking conflict logic**
   - Files: `app/routers/bookings.py`
   - Issue: conflict detection used `<=` comparisons, which treated back-to-back intervals as overlapping and returned `409 ROOM_CONFLICT` incorrectly.
   - Fix: changed overlap detection to `existing.start_time < new.end and new.start < existing.end`.
   - Difficulty: Easy — interval boundary bug.

4. **Booking pagination ordering wrong**
   - Files: `app/routers/bookings.py`
   - Issue: `GET /bookings` sorted bookings descending by `start_time` instead of ascending, violating rule 11.
   - Fix: changed ordering to `Booking.start_time.asc(), Booking.id.asc()`.
   - Difficulty: Easy — ordering bug.

5. **Incorrect availability query semantics**
   - Files: `app/routers/rooms.py`
   - Issue: room availability returned bookings overlapping the requested date, not only bookings that start on that UTC date.
   - Fix: changed availability filter to `Booking.start_time >= day_start` and `Booking.start_time < day_end`.
   - Difficulty: Medium — business-rule interpretation.

6. **Refund rounding and stored amount mismatch**
   - Files: `app/routers/bookings.py`, `app/services/refunds.py`
   - Issue: refund rounding used Python `round()`, which is banker's rounding, and `services/refunds.log_refund` used integer floor division. This failed rule 6 half-cent round-up and made response amounts potentially inconsistent with stored logs.
   - Fix: compute amount with half-up formula `(price_cents * percent + 50) // 100`, store that value in the refund log, and return the stored amount.
   - Difficulty: Medium — rounding rule.

7. **Refresh tokens were not single-use**
   - Files: `app/auth.py`, `app/routers/auth.py`
   - Issue: `POST /auth/refresh` did not revoke the presented refresh token, so it could be reused indefinitely until expiration.
   - Fix: added refresh token deny list and revoke old refresh tokens on rotation.
   - Difficulty: Medium — auth flow bug.

8. **Rate limiter not concurrency-safe**
   - Files: `app/services/ratelimit.py`
   - Issue: bucket updates were performed without synchronization, risking incorrect counts under concurrent `POST /bookings` requests.
   - Fix: added a lock around rate-limiter bucket maintenance.
   - Difficulty: Medium — concurrency safety.

9. **Room stats updates were not concurrency-safe**
   - Files: `app/services/stats.py`
   - Issue: incremental stats updates used non-atomic read-modify-write on a shared dict, risking lost updates under concurrent booking/cancellation bursts.
   - Fix: added a lock around stats updates.
   - Difficulty: Medium — concurrency safety.

10. **Booking creation did not invalidate usage report cache**
    - Files: `app/routers/bookings.py`
    - Issue: new confirmed bookings could leave cached admin usage reports stale.
    - Fix: invalidate report cache after booking creation.
    - Difficulty: Medium — cache invalidation.

11. **Cancellation did not invalidate room availability cache**
    - Files: `app/routers/bookings.py`
    - Issue: cancelled bookings could remain visible in cached room availability.
    - Fix: invalidate availability cache for the affected room/date on cancellation.
    - Difficulty: Medium — cache invalidation.

12. **Concurrent cancellation could create duplicate refunds**
    - Files: `app/models.py`, `app/services/refunds.py`, `app/routers/bookings.py`
    - Issue: concurrent cancel requests could produce duplicate `RefundLog` rows because there was no unique constraint or atomic cancellation handling.
    - Fix: added a unique constraint on `refund_logs.booking_id`, changed refund logging to flush within the same transaction, and handled duplicate-insert integrity failures as `ALREADY_CANCELLED`.
    - Difficulty: Hard — concurrency and DB integrity.

13. **Reference codes and refund logs lacked DB-level uniqueness guarantees**
    - Files: `app/models.py`
    - Issue: `reference_code` and `refund_logs.booking_id` were not guaranteed unique by the schema.
    - Fix: added unique constraints for `Booking.reference_code` and `RefundLog.booking_id`.
    - Difficulty: Medium — data integrity.

14. **Export room filter did not enforce org scoping for room_id**
    - Files: `app/routers/admin.py`
    - Issue: `/admin/export?room_id=` could silently return empty CSV for a cross-org or invalid room rather than `404 ROOM_NOT_FOUND`.
    - Fix: validate the requested room belongs to the caller's org and return `404` if not.
    - Difficulty: Medium — multi-tenancy validation.

## Verification

- `./venv/bin/python -m pytest -q` → `12 passed`
- Added regression coverage in `tests/test_bug_hunt.py`
