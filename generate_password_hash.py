#!/usr/bin/env python3
"""
Script to generate a password hash for the admin authentication system.
Run this script to generate a hash for your desired password.
"""

from passlib.context import CryptContext
import getpass
import sys

def main():
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    print("=== Password Hash Generator ===")
    print("This script will generate a bcrypt hash for your admin password.")
    print("You'll need to add this hash to your environment variables.")
    print()
    
    try:
        # Get password from user
        password = getpass.getpass("Enter your desired admin password: ")
        
        if not password:
            print("Error: Password cannot be empty")
            sys.exit(1)
        
        # Confirm password
        confirm_password = getpass.getpass("Confirm password: ")
        
        if password != confirm_password:
            print("Error: Passwords do not match")
            sys.exit(1)
        
        # Generate hash
        print("\nGenerating password hash...")
        password_hash = pwd_context.hash(password)
        
        print("\n=== SUCCESS ===")
        print("Your password hash has been generated!")
        print("\nAdd this to your .env file:")
        print(f"ADMIN_PASSWORD_HASH={password_hash}")
        print(f"SECRET_KEY=your-secret-key-change-this-to-something-random")
        print("\nFor production, make sure to:")
        print("1. Use a strong, random SECRET_KEY")
        print("2. Keep these values secure and never commit them to version control")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()