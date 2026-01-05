#!/usr/bin/env python
"""
Quick setup script for Invoice Maker application
Run this after setting up your virtual environment and installing dependencies
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"\n{'='*60}")
    print(f"📌 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        print(f"✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"Error: {e.stderr}")
        return False

def create_directories():
    """Create required directories"""
    print("\n📁 Creating required directories...")
    
    directories = [
        'static/css',
        'static/js',
        'media/logos',
        'templates/registration',
        'templates/invoices'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   ✓ Created {directory}")
    
    print("✅ All directories created")

def create_env_file():
    """Create .env file if it doesn't exist"""
    if not os.path.exists('.env'):
        print("\n📝 Creating .env file...")
        
        env_content = """SECRET_KEY=django-insecure-change-this-in-production
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3

# For PostgreSQL, uncomment and configure:
# DATABASE_URL=postgresql://username:password@localhost:5432/invoice_maker_db
"""
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("✅ .env file created")
    else:
        print("\n✓ .env file already exists")

def create_gitignore():
    """Create .gitignore file"""
    if not os.path.exists('.gitignore'):
        print("\n📝 Creating .gitignore...")
        
        gitignore_content = """*.pyc
__pycache__/
*.sqlite3
db.sqlite3
venv/
.env
*.log
staticfiles/
media/
.DS_Store
*.swp
.vscode/
.idea/
"""
        with open('.gitignore', 'w') as f:
            f.write(gitignore_content)
        
        print("✅ .gitignore created")
    else:
        print("\n✓ .gitignore already exists")

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║         🧾 INVOICE MAKER - SETUP SCRIPT 🧾              ║
║                                                          ║
║  This script will set up your Django application        ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")

    # Check if we're in a virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  WARNING: You don't appear to be in a virtual environment!")
        print("   It's recommended to activate your virtual environment first.")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            return

    # Create directories
    create_directories()
    
    # Create .env file
    create_env_file()
    
    # Create .gitignore
    create_gitignore()
    
    # Run Django management commands
    steps = [
        ("python manage.py makemigrations", "Creating database migrations"),
        ("python manage.py migrate", "Applying database migrations"),
        ("python manage.py collectstatic --noinput", "Collecting static files"),
    ]
    
    for command, description in steps:
        if not run_command(command, description):
            print(f"\n⚠️  Failed at: {description}")
            print("You may need to run this command manually")
    
    # Create superuser
    print(f"\n{'='*60}")
    print("👤 Creating Superuser")
    print(f"{'='*60}")
    print("Please enter details for the admin account:")
    
    try:
        subprocess.run("python manage.py createsuperuser", shell=True, check=True)
        print("✅ Superuser created successfully")
    except subprocess.CalledProcessError:
        print("⚠️  Superuser creation skipped or failed")
    
    # Final message
    print(f"\n{'='*60}")
    print("🎉 SETUP COMPLETE!")
    print(f"{'='*60}")
    print("""
Next steps:

1. Start the development server:
   python manage.py runserver

2. Open your browser and visit:
   http://127.0.0.1:8000

3. Login with your superuser credentials

4. Set up your business profile

5. Start creating invoices!

📚 For more information, check the README.md file

💡 Tips:
   - Access admin panel at: http://127.0.0.1:8000/admin
   - Toggle dark mode using the moon/sun icon
   - Ad click tracking is automatically enabled

Need help? Check the troubleshooting section in README.md
""")

if __name__ == '__main__':
    main()