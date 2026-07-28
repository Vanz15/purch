"""Purch Reflex application package.

Single source of truth for the Reflex shell. The sole `rx.App` instance
lives in `purch/purch.py`; every page, component, and state class is
imported from there so Reflex discovery only ever finds one App.
"""
