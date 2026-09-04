CREATE TABLE IF NOT EXISTS cities (
    city_id SERIAL PRIMARY KEY,
    city_name VARCHAR(80) UNIQUE NOT NULL,
    state_name VARCHAR(80) NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(80) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(150) UNIQUE NOT NULL,
    category_id INT NOT NULL REFERENCES categories(category_id),
    base_cost NUMERIC(12,2) NOT NULL CHECK (base_cost >= 0),
    list_price NUMERIC(12,2) NOT NULL CHECK (list_price >= 0)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id BIGSERIAL PRIMARY KEY,
    customer_name VARCHAR(120) NOT NULL,
    city_id INT NOT NULL REFERENCES cities(city_id)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    order_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL CHECK (status IN ('DELIVERED','SHIPPED','PROCESSING','CANCELLED'))
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INT NOT NULL REFERENCES products(product_id),
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    unit_cost_at_order NUMERIC(12,2) NOT NULL CHECK (unit_cost_at_order >= 0),
    discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    gross_revenue NUMERIC(14,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    revenue NUMERIC(14,2) GENERATED ALWAYS AS ((quantity * unit_price) - discount_amount) STORED,
    cost NUMERIC(14,2) GENERATED ALWAYS AS (quantity * unit_cost_at_order) STORED,
    profit NUMERIC(14,2) GENERATED ALWAYS AS (
        GREATEST(((quantity * unit_price) - discount_amount) - (quantity * unit_cost_at_order), 0)
    ) STORED,
    loss NUMERIC(14,2) GENERATED ALWAYS AS (
        GREATEST((quantity * unit_cost_at_order) - ((quantity * unit_price) - discount_amount), 0)
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_year ON orders((EXTRACT(YEAR FROM order_date)));
CREATE INDEX IF NOT EXISTS idx_customers_city_id ON customers(city_id);
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);

CREATE OR REPLACE VIEW order_facts AS
SELECT
    o.order_id,
    o.order_date,
    EXTRACT(YEAR FROM o.order_date)::INT AS year,
    c.customer_id,
    c.customer_name,
    ci.city_name AS city,
    ci.state_name AS state,
    cat.category_name AS category,
    p.product_name AS product,
    oi.quantity,
    oi.unit_price,
    oi.gross_revenue,
    oi.revenue,
    oi.cost,
    oi.profit,
    oi.loss,
    o.status
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN cities ci ON ci.city_id = c.city_id
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p ON p.product_id = oi.product_id
JOIN categories cat ON cat.category_id = p.category_id;
