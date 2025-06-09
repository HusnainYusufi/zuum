#!/usr/bin/env python3
"""
Script to reinitialize the database with dummy data.
Run this script to reset the database and add test data.
"""

from init_db import init_db

if __name__ == "__main__":
    print("Reinitializing database...")
    init_db()
    print("Database reinitialized successfully!") 