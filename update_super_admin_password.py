"""
Script to update the super admin password.

This script allows you to:
1. Create a super admin account if it doesn't exist
2. Update the password for an existing super admin
3. Promote an existing user to super admin

Usage:
    python update_super_admin_password.py
"""

from app import create_app, db
from app.models import User
import getpass

def main():
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("CareerJet - Super Admin Password Management")
        print("=" * 60)
        print()
        
        # Get email
        email = input("Enter super admin email: ").strip()
        
        if not email:
            print("Error: Email cannot be empty.")
            return
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if user:
            print(f"\nUser found: {email}")
            print(f"Current status:")
            print(f"  - Is Admin: {user.is_admin}")
            print(f"  - Is Super Admin: {user.is_super_admin}")
            print()
            
            # Ask what to do
            print("What would you like to do?")
            print("1. Update password")
            print("2. Promote to super admin (and update password)")
            print("3. Cancel")
            
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == "3":
                print("Operation cancelled.")
                return
            elif choice not in ["1", "2"]:
                print("Invalid choice. Operation cancelled.")
                return
            
            # Get new password
            while True:
                password = getpass.getpass("Enter new password: ")
                password_confirm = getpass.getpass("Confirm new password: ")
                
                if password != password_confirm:
                    print("Passwords do not match. Please try again.\n")
                    continue
                
                if len(password) < 6:
                    print("Password must be at least 6 characters long. Please try again.\n")
                    continue
                
                break
            
            # Update user
            user.set_password(password)
            
            if choice == "2":
                user.is_admin = True
                user.is_super_admin = True
                print("\nPromoting user to super admin...")
            
            db.session.commit()
            
            print("\n" + "=" * 60)
            print("✓ Password updated successfully!")
            if choice == "2":
                print("✓ User promoted to super admin!")
            print("=" * 60)
            print(f"\nUpdated user details:")
            print(f"  - Email: {user.email}")
            print(f"  - Is Admin: {user.is_admin}")
            print(f"  - Is Super Admin: {user.is_super_admin}")
            
        else:
            print(f"\nUser not found: {email}")
            print("\nWould you like to create a new super admin account?")
            create = input("Enter 'yes' to create, anything else to cancel: ").strip().lower()
            
            if create != 'yes':
                print("Operation cancelled.")
                return
            
            # Get password for new user
            while True:
                password = getpass.getpass("Enter password: ")
                password_confirm = getpass.getpass("Confirm password: ")
                
                if password != password_confirm:
                    print("Passwords do not match. Please try again.\n")
                    continue
                
                if len(password) < 6:
                    print("Password must be at least 6 characters long. Please try again.\n")
                    continue
                
                break
            
            # Create new super admin
            new_user = User(email=email)
            new_user.set_password(password)
            new_user.is_admin = True
            new_user.is_super_admin = True
            
            db.session.add(new_user)
            db.session.commit()
            
            print("\n" + "=" * 60)
            print("✓ Super admin account created successfully!")
            print("=" * 60)
            print(f"\nNew user details:")
            print(f"  - Email: {new_user.email}")
            print(f"  - Is Admin: {new_user.is_admin}")
            print(f"  - Is Super Admin: {new_user.is_super_admin}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
