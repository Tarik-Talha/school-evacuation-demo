"""Illustrative external-response timing based on published Istanbul averages.

These are citywide reference values, not route-level predictions for the school.
The scenario assumes both services are notified after shaking ends and applies
the published average as the response interval after notification.
"""
from __future__ import annotations

import math


PUBLIC_REFERENCES = {
    "ambulance": {
        "label": "İBB 2024 · Acil sağlık vakalarına ortalama varış",
        "seconds": 5 * 60 + 44,
        "url": "https://uploads.ibb.istanbul/uploads/2026_Performans_Programi_b33fca6500.pdf",
    },
    "fire": {
        "label": "İBB 2024 · İtfai olaylarına ortalama varış",
        "seconds": 6 * 60 + 44,
        "url": "https://uploads.ibb.istanbul/uploads/2026_Performans_Programi_b33fca6500.pdf",
    },
}


def format_duration(seconds: float) -> str:
    """Format a non-negative duration in a compact Turkish UI form."""
    whole_seconds = round(seconds)
    minutes, remainder = divmod(whole_seconds, 60)
    if minutes >= 60:
        hours, minutes = divmod(minutes, 60)
        return f"{hours} sa {minutes} dk {remainder:02d} sn"
    return f"{minutes} dk {remainder:02d} sn"


def estimate_external_arrivals(
    shaking_seconds: float,
    call_delay_after_shaking_seconds: float = 0,
) -> dict:
    """Return illustrative arrival times for the two services.

    ``call_delay_after_shaking_seconds`` is added after shaking ends. The
    citywide response reference is then applied after that simulated call.
    """
    for name, value, upper in (
        ("shaking_seconds", shaking_seconds, 300),
        ("call_delay_after_shaking_seconds", call_delay_after_shaking_seconds, 600),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"Invalid {name}")
        if not 0 <= value <= upper:
            raise ValueError(f"{name} is outside the supported range")

    delay = float(call_delay_after_shaking_seconds)
    shaking = float(shaking_seconds)
    arrivals = {}
    for service, reference in PUBLIC_REFERENCES.items():
        after_shaking = delay + reference["seconds"]
        from_earthquake = shaking + after_shaking
        arrivals[service] = {
            "reference_seconds": reference["seconds"],
            "reference_label": reference["label"],
            "reference_url": reference["url"],
            "call_delay_after_shaking_seconds": delay,
            "arrival_after_shaking_seconds": after_shaking,
            "arrival_from_earthquake_seconds": from_earthquake,
            "arrival_after_shaking_label": format_duration(after_shaking),
            "arrival_from_earthquake_label": format_duration(from_earthquake),
        }

    return {
        "services": arrivals,
        "shaking_seconds": shaking,
        "call_delay_after_shaking_seconds": delay,
        "call_assumption": "Her iki ekibin de sarsıntı bittikten sonra bildirildiği varsayılır; bildirim gecikmesi kullanıcı girdisidir.",
        "reference_scope": "İBB'nin İstanbul geneli 2024 gerçekleşme ortalamalarıdır; okul adresine veya deprem sonrası yol koşullarına özel değildir.",
        "traffic_adjustment": "Yok; trafik, ekip müsaitliği, deprem hasarı ve yol kapanmaları ayrıca modellenmedi.",
    }
