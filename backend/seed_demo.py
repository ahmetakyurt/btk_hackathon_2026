"""Demo seed script SKIP creates 5 realistic products via the backend API.

Usage:
    cd backend
    python seed_demo.py [--url http://localhost:8000]

Skips products whose SKU already exists (idempotent).
"""

from __future__ import annotations

import argparse
import sys
import time

import httpx

PRODUCTS = [
    {
        "sku": "SONY-WH1000XM5",
        "title": "Sony WH-1000XM5 Kablosuz Gürültü Engelleyici Kulaklık",
        "base_cost": 2800.00,
        "shipping_cost": 35.00,
        "stock": 50,
        "category": "Elektronik / Kulaklık",
        "initial_price": 4299.00,
        "raw_specs": {
            "marka": "Sony",
            "model": "WH-1000XM5",
            "bağlantı": "Bluetooth 5.2",
            "pil_ömrü": "30 saat",
            "anc": "Evet",
            "renk": "Siyah",
        },
    },
    {
        "sku": "PHILIPS-AF9252",
        "title": "Philips Essential Airfryer XXL 6.2L Yağsız Fritöz",
        "base_cost": 1450.00,
        "shipping_cost": 50.00,
        "stock": 30,
        "category": "Ev & Yaşam / Mutfak Aletleri",
        "initial_price": 2249.00,
        "raw_specs": {
            "marka": "Philips",
            "model": "HD9252/91",
            "kapasite": "6.2 litre",
            "güç": "2000W",
            "kontrol": "Dijital",
            "renk": "Siyah",
        },
    },
    {
        "sku": "XIAOMI-MIBAND9",
        "title": "Xiaomi Mi Band 9 Akilli Bileklik - AMOLED Ekran",
        "base_cost": 450.00,
        "shipping_cost": 15.00,
        "stock": 120,
        "category": "Elektronik / Giyilebilir",
        "initial_price": 849.00,
        "raw_specs": {
            "marka": "Xiaomi",
            "model": "Mi Band 9",
            "ekran": "1.62\" AMOLED",
            "su_geçirmezlik": "5 ATM",
            "pil_ömrü": "21 gün",
            "sensörler": "Nabız, SpO2, Uyku",
        },
    },
    {
        "sku": "TEFAL-KO8501",
        "title": "Tefal Smart'n Light Elektrikli Su Isıtıcı 1.7L",
        "base_cost": 320.00,
        "shipping_cost": 20.00,
        "stock": 80,
        "category": "Ev & Yaşam / Küçük Ev Aletleri",
        "initial_price": 599.00,
        "raw_specs": {
            "marka": "Tefal",
            "model": "KO850130",
            "kapasite": "1.7 litre",
            "güç": "2400W",
            "malzeme": "Cam",
            "garanti": "2 yıl",
        },
    },
    {
        "sku": "LOGITECH-MX3S",
        "title": "Logitech MX Master 3S Kablosuz Performans Mouse",
        "base_cost": 950.00,
        "shipping_cost": 20.00,
        "stock": 60,
        "category": "Bilgisayar / Çevre Birimleri",
        "initial_price": 1699.00,
        "raw_specs": {
            "marka": "Logitech",
            "model": "MX Master 3S",
            "bağlantı": "Bluetooth / USB-C",
            "dpi": "200-8000",
            "pil": "Şarj edilebilir",
            "uyumluluk": "Windows, macOS, Linux",
        },
    },
]


def seed(base_url: str) -> None:
    client = httpx.Client(base_url=base_url, timeout=60.0)

    # Health check
    try:
        r = client.get("/health")
        r.raise_for_status()
        print(f"OK Backend: {base_url}")
    except Exception as exc:
        print(f"FAIL Backend unreachable: {exc}", file=sys.stderr)
        sys.exit(1)

    created = 0
    skipped = 0

    for p in PRODUCTS:
        sku = p["sku"]
        try:
            r = client.post("/api/products", json=p)
            if r.status_code == 201:
                product = r.json()
                statuses = product.get("platform_statuses", [])
                listed = sum(1 for s in statuses if s["status"] == "listed")
                print(f"  OK {sku} SKIP {listed}/{len(statuses)} platformda listelendi")
                created += 1
                time.sleep(0.5)  # gentle pacing for ListingAgent
            elif r.status_code == 409:
                print(f"  SKIP {sku} zaten var, atlanıyor")
                skipped += 1
            else:
                print(f"  FAIL {sku}: {r.status_code} {r.text[:120]}", file=sys.stderr)
        except Exception as exc:
            print(f"  FAIL {sku}: {exc}", file=sys.stderr)

    print(f"\nTamamlandı: {created} yeni, {skipped} mevcut.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    seed(args.url)
