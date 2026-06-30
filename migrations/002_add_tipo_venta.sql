-- Migration: Add tipo_venta, precio_por_kilo, precio_por_unidad to productos
--             Add por_kilo, peso to venta_items
-- Date: 2026-06-30

-- Productos: tipo_venta (null = 'unidad' for backwards compatibility)
ALTER TABLE productos ADD COLUMN tipo_venta TEXT DEFAULT 'unidad' CHECK(tipo_venta IN ('unidad', 'kilo', 'ambos'));

-- Productos: precio por kilo (for panaderia, fiambres, rotiserías)
ALTER TABLE productos ADD COLUMN precio_por_kilo REAL;

-- Productos: precio por unidad (when tipo_venta = 'ambos')
ALTER TABLE productos ADD COLUMN precio_por_unidad REAL;

-- Venta items: whether this item was sold by kilo
ALTER TABLE venta_items ADD COLUMN por_kilo INTEGER DEFAULT 0;

-- Venta items: weight in kg (used when por_kilo = 1)
ALTER TABLE venta_items ADD COLUMN peso REAL;
