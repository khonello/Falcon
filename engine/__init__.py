"""Falcon Engine — the single source of truth (implementation-spec.md §3).

Owns the database, the Global File Index, the audit trail, and all Hierarchy / Task / Flow /
Resource / Control-Events-Monitoring business logic. Every other package is a thin client.
"""
