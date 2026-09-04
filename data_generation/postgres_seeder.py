#!/usr/bin/env python3
import random
from decimal import Decimal

from datetime import date, timedelta
import psycopg2
from faker import Faker
from psycopg2.extras import execute_values

DB_HOST = "localhost"
DB_NAME = "stayspot"
DB_USER = "postgres"
DB_PASSWORD = "Alfa@123"

GUEST_COUNT = 10000
PROPERTY_COUNT = 5000
BOOKING_COUNT = 100000

fake = Faker()


def connect():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def generate_data():
    conn = connect()
    cur = conn.cursor()

    print("Inserting guests...")
    guest_rows = [
        (fake.name(), round(random.uniform(1000, 10000), 2))
        for _ in range(GUEST_COUNT)
    ]
    guest_ids = execute_values(
        cur,
        "INSERT INTO guests (name, wallet_balance) VALUES %s RETURNING id, wallet_balance",
        guest_rows,
        fetch=True,
    )
    conn.commit()
    print(f"Inserted {len(guest_ids)} guests.")

    print("Inserting properties...")
    property_rows = [
        (
            fake.sentence(nb_words=4).rstrip("."),
            round(random.uniform(50, 200), 2),
            random.uniform(40.70, 40.80),
            random.uniform(-74.05, -73.85),
        )
        for _ in range(PROPERTY_COUNT)
    ]
    property_ids = execute_values(
        cur,
        "INSERT INTO properties (title, base_price, latitude, longitude) VALUES %s RETURNING id, base_price",
        property_rows,
        fetch=True,
    )
    conn.commit()
    print(f"Inserted {len(property_ids)} properties.")

    guests = [[row[0], Decimal(row[1])] for row in guest_ids]
    properties = [(row[0], Decimal(row[1])) for row in property_ids]
    checked_in = set()

    print("Inserting bookings and updating wallets...")
    inserted = 0
    while inserted < BOOKING_COUNT:
        check_in = date.today() + timedelta(days=random.randint(1, 30))
        check_out = check_in + timedelta(days=random.randint(2, 7))
        g_idx = random.randrange(len(guests))
        guest_id, balance = guests[g_idx]
        property_id, base_price = random.choice(properties)
        nights = (check_out - check_in).days
        total_cost = (base_price * nights).quantize(Decimal("0.01"))

        

        if balance < total_cost:
            continue

        if guest_id not in checked_in and random.random() < 0.02:
            status = "CHECKED_IN"
            checked_in.add(guest_id)
        elif random.random() < 0.5:
            status = "COMPLETED"
        else:
            status = "CONFIRMED"

        cur.execute(
            "UPDATE guests SET wallet_balance = wallet_balance - %s WHERE id = %s",
            (total_cost, guest_id),
        )
        cur.execute(
                    """INSERT INTO bookings
                    (guest_id, property_id, check_in, check_out, total_cost, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (guest_id, property_id, check_in, check_out, total_cost, status),
                )
        guests[g_idx][1] = balance - total_cost
        inserted += 1

        if inserted % 1000 == 0:
            conn.commit()
            print(f"Inserted {inserted} bookings...")

    conn.commit()
    print(f"Inserted {inserted} bookings.")

    cur.execute("SELECT COUNT(*) FROM guests")
    print("Guests:", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM properties")
    print("Properties:", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM bookings")
    print("Bookings:", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM wallet_audit_logs")
    print("Wallet Audit Logs:", cur.fetchone()[0])

    cur.close()
    conn.close()


if __name__ == "__main__":
    generate_data()
