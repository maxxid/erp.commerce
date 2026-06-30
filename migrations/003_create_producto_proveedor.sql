-- Migration: Create producto_proveedor association table
-- Date: 2026-06-30

CREATE TABLE IF NOT EXISTS producto_proveedor (
    producto_id INTEGER NOT NULL,
    proveedor_id INTEGER NOT NULL,
    PRIMARY KEY (producto_id, proveedor_id),
    FOREIGN KEY (producto_id) REFERENCES productos(id),
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
);
