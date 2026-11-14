from datetime import date, timedelta
import random
from sqlalchemy import create_engine, text
from app.config import DATABASE_URL
import os

random.seed(17)
engine = create_engine(os.getenv("SEED_DATABASE_URL", DATABASE_URL.replace("analytics_user:analytics_pass", "analytics_admin:admin_demo_password")))

with engine.begin() as conn:
    conn.execute(text("""
    DROP TABLE IF EXISTS order_items, orders, products, customers CASCADE;
    CREATE TABLE customers (customer_id SERIAL PRIMARY KEY, customer_name VARCHAR(100), city VARCHAR(60), segment VARCHAR(30));
    CREATE TABLE products (product_id SERIAL PRIMARY KEY, product_name VARCHAR(100), category VARCHAR(50), unit_price NUMERIC(10,2));
    CREATE TABLE orders (order_id SERIAL PRIMARY KEY, customer_id INT REFERENCES customers(customer_id), order_date DATE, status VARCHAR(20));
    CREATE TABLE order_items (item_id SERIAL PRIMARY KEY, order_id INT REFERENCES orders(order_id), product_id INT REFERENCES products(product_id), quantity INT, unit_price NUMERIC(10,2));
    """))
    cities = ["New York", "Chicago", "Austin", "Seattle", "Boston", "Denver"]
    segments = ["Consumer", "Corporate", "Small Business"]
    for i in range(60):
        conn.execute(text("INSERT INTO customers(customer_name,city,segment) VALUES (:n,:c,:s)"), {"n":f"Customer {i+1:03}","c":random.choice(cities),"s":random.choice(segments)})
    products = [("Laptop", "Electronics", 850), ("Monitor", "Electronics", 220), ("Desk Chair", "Furniture", 180), ("Notebook Pack", "Office Supplies", 12), ("Desk", "Furniture", 320), ("Headphones", "Electronics", 75), ("Printer Paper", "Office Supplies", 18), ("Webcam", "Electronics", 55)]
    for n,c,p in products:
        conn.execute(text("INSERT INTO products(product_name,category,unit_price) VALUES (:n,:c,:p)"), {"n":n,"c":c,"p":p})
    start = date(2025,1,1)
    for i in range(500):
        cust = random.randint(1,60)
        od = start + timedelta(days=random.randint(0, 640))
        oid = conn.execute(text("INSERT INTO orders(customer_id,order_date,status) VALUES (:c,:d,:s) RETURNING order_id"), {"c":cust,"d":od,"s":random.choice(["Shipped","Delivered","Processing"]) }).scalar_one()
        for _ in range(random.randint(1,4)):
            pid = random.randint(1,len(products)); qty=random.randint(1,5)
            price = products[pid-1][2]
            conn.execute(text("INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (:o,:p,:q,:u)"), {"o":oid,"p":pid,"q":qty,"u":price})
print("Seeded 60 customers, 8 products, 500 orders and their order items.")
