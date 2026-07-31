"""NS departure delay statistics.

Layered on purpose, each layer depending only on the one above it:
    client    -> HTTP only, returns raw JSON
    transform -> raw JSON to typed `Departure` records
    aggregate -> records to per-category statistics
    cli       -> wiring and terminal output
"""
