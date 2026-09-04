TRUNCATE TABLE order_items, orders, customers, products, categories, cities RESTART IDENTITY CASCADE;

INSERT INTO cities (city_name, state_name) VALUES
('Hyderabad','Telangana'),
('Bengaluru','Karnataka'),
('Mumbai','Maharashtra'),
('Delhi','Delhi'),
('Chennai','Tamil Nadu'),
('Pune','Maharashtra'),
('Kolkata','West Bengal'),
('Ahmedabad','Gujarat'),
('Jaipur','Rajasthan'),
('Kochi','Kerala');

INSERT INTO categories (category_name) VALUES
('Clothing'),('Electronics'),('Furniture'),('Grocery'),('Beauty'),('Sports'),('Books'),('Home & Kitchen');

INSERT INTO products (product_name, category_id, base_cost, list_price) VALUES
('Cotton Shirt',1,550,999),('Denim Jeans',1,900,1599),('Running T-Shirt',1,400,799),
('Wireless Earbuds',2,1400,2499),('Smart Watch',2,2800,4999),('Bluetooth Speaker',2,1100,1999),
('Office Chair',3,3200,5499),('Study Table',3,4200,6999),('Bookshelf',3,2500,4499),
('Premium Rice 5kg',4,420,699),('Cooking Oil 5L',4,620,899),('Dry Fruits Pack',4,700,1199),
('Skin Care Kit',5,850,1499),('Hair Dryer',5,950,1699),('Perfume',5,1200,2199),
('Yoga Mat',6,550,999),('Cricket Bat',6,1800,2999),('Running Shoes',6,1600,2799),
('Business Book',7,250,499),('Programming Book',7,450,799),('Children Story Set',7,300,599),
('Cookware Set',8,1800,3199),('Bedsheet Set',8,700,1299),('Mixer Grinder',8,2200,3999);

INSERT INTO customers (customer_name, city_id)
SELECT 'Customer ' || LPAD(g::text, 4, '0'), ((g * 7) % 10) + 1
FROM generate_series(1, 1200) AS g;

-- Persisted orders cover 2019-2025 and extend through the database current date so relative-date demos remain meaningful after 2025.
INSERT INTO orders (customer_id, order_date, status)
SELECT
    ((g * 17) % 1200) + 1,
    DATE '2019-01-01' + (((g * 37) % ((CURRENT_DATE - DATE '2019-01-01') + 1))::INT),
    CASE
        WHEN g % 25 = 0 THEN 'CANCELLED'
        WHEN g % 9 = 0 THEN 'PROCESSING'
        WHEN g % 5 = 0 THEN 'SHIPPED'
        ELSE 'DELIVERED'
    END
FROM generate_series(1, 36000) AS g;

-- 1-3 items per order. Values are deterministic, not generated at query time.
INSERT INTO order_items (
    order_id, product_id, quantity, unit_price, unit_cost_at_order, discount_amount
)
SELECT
    o.order_id,
    p.product_id,
    1 + ((o.order_id + item_no) % 4)::INT AS quantity,
    ROUND((p.list_price * (1 + ((EXTRACT(YEAR FROM o.order_date)::INT - 2019) * 0.025)))::NUMERIC, 2) AS unit_price,
    ROUND((
        p.base_cost
        * (1 + ((EXTRACT(YEAR FROM o.order_date)::INT - 2019) * 0.03))
        * CASE WHEN (o.order_id + item_no) % 19 = 0 THEN 1.55 ELSE 1 END
    )::NUMERIC, 2) AS unit_cost_at_order,
    ROUND((
        (1 + ((o.order_id + item_no) % 4)::INT)
        * p.list_price
        * (1 + ((EXTRACT(YEAR FROM o.order_date)::INT - 2019) * 0.025))
        * CASE
            WHEN (o.order_id + item_no) % 23 = 0 THEN 0.35
            ELSE (((o.order_id + item_no) % 5) * 0.025)
          END
    )::NUMERIC, 2) AS discount_amount
FROM orders o
CROSS JOIN LATERAL generate_series(1, 1 + (o.order_id % 3)::INT) AS item_no
JOIN products p ON p.product_id = (((o.order_id * 7 + item_no * 11) % 24) + 1)::INT;

ANALYZE;
