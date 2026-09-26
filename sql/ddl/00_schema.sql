-- AutoCare Intelligence — Enterprise Data Warehouse DDL
-- File: 00_schema.sql
-- Target Database: PostgreSQL 16+
-- Schema: autocare_dw

CREATE SCHEMA IF NOT EXISTS autocare_dw;

COMMENT ON SCHEMA autocare_dw IS 'AutoCare Intelligence Enterprise Data Warehouse dimensional star schema conforming to AutoCare_Intelligence.pdf Section 7.';
