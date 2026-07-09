"""Shared response serialization for bookings."""
from enum import Enum

from .models import Booking
from .timeutils import iso_utc


def _to_iso(dt):
    return iso_utc(dt) if dt is not None else None


def serialize_booking(booking: Booking) -> dict:
    return {
        "id": booking.id,
        "reference_code": booking.reference_code,
        "room_id": booking.room_id,
        "user_id": booking.user_id,
        "start_time": _to_iso(booking.start_time),
        "end_time": _to_iso(booking.end_time),
        "status": booking.status.value if isinstance(booking.status, Enum) else booking.status,
        "price_cents": booking.price_cents,
        "created_at": _to_iso(booking.created_at),
    }
