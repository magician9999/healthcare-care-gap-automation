#!/usr/bin/env python3
"""
Project Setup Script
Initializes the healthcare care gap automation project with database and sample data.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description="", cwd=None):
    """Run a shell command and handle errors"""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, cwd=cwd, capture_output=True, text=True)
        if result.stdout.strip():
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e}")
        if e.stderr:
            print(f"   Error details: {e.stderr}")
        return False

def check_requirements():
    """Check if required tools are installed"""
    print("🔍 Checking requirements...")
    
    requirements = [
        ("python3", "Python 3"),
        ("docker", "Docker"),
        ("docker-compose", "Docker Compose")
    ]
    
    missing = []
    for cmd, name in requirements:
        try:
            subprocess.run([cmd, "--version"], check=True, capture_output=True)
            print(f"   ✅ {name} is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"   ❌ {name} is not installed")
            missing.append(name)
    
    if missing:
        print(f"\n⚠️  Please install the following requirements: {', '.join(missing)}")
        return False
    return True

def setup_environment():
    """Set up the environment file"""
    print("🌍 Setting up environment...")
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("   ✅ Created .env file from .env.example")
        print("   📝 Please update the .env file with your specific configuration")
    else:
        print("   ℹ️  .env file already exists")
    
    return True

def setup_python_environment():
    """Set up Python virtual environment and install dependencies"""
    print("🐍 Setting up Python environment...")
    
    # Create virtual environment if it doesn't exist
    if not Path(".venv").exists():
        if not run_command("python3 -m venv .venv", "Creating virtual environment"):
            return False
    else:
        print("   ℹ️  Virtual environment already exists")
    
    # Install requirements
    if sys.platform.startswith('win'):
        pip_path = ".venv/Scripts/pip"
        python_path = ".venv/Scripts/python"
    else:
        pip_path = ".venv/bin/pip"
        python_path = ".venv/bin/python"
    
    if not run_command(f"{pip_path} install --upgrade pip", "Upgrading pip"):
        return False
    
    if not run_command(f"{pip_path} install -r requirements.txt", "Installing Python dependencies"):
        return False
    
    return True

def setup_database():
    """Set up the database using Docker Compose"""
    print("🗄️  Setting up database...")
    
    # Start PostgreSQL
    if not run_command("docker-compose up -d postgres", "Starting PostgreSQL database"):
        return False
    
    # Wait a moment for database to start
    print("   ⏳ Waiting for database to start...")
    import time
    time.sleep(10)
    
    return True

def run_migrations():
    """Initialize and run database migrations"""
    print("🔄 Setting up database migrations...")
    
    backend_dir = Path("backend")
    
    if sys.platform.startswith('win'):
        python_path = "../.venv/Scripts/python"
        alembic_path = "../.venv/Scripts/alembic"
    else:
        python_path = "../.venv/bin/python"
        alembic_path = "../.venv/bin/alembic"
    
    # Initialize Alembic if not already done
    if not Path("backend/alembic/versions").exists() or not any(Path("backend/alembic/versions").iterdir()):
        if not run_command(f"{alembic_path} revision --autogenerate -m 'Initial migration'", "Creating initial migration", cwd=backend_dir):
            return False
    
    # Run migrations
    if not run_command(f"{alembic_path} upgrade head", "Running database migrations", cwd=backend_dir):
        return False
    
    return True

def generate_sample_data():
    """Generate sample patient data"""
    print("📊 Generating sample data...")
    
    if sys.platform.startswith('win'):
        python_path = ".venv/Scripts/python"
    else:
        python_path = ".venv/bin/python"
    
    if not run_command(f"{python_path} scripts/generate_sample_data.py", "Generating sample patient data"):
        return False
    
    return True

def main():
    """Main setup function"""
    print("🏥 Healthcare Care Gap Automation - Project Setup")
    print("=" * 50)
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    steps = [
        ("Check requirements", check_requirements),
        ("Setup environment", setup_environment),
        ("Setup Python environment", setup_python_environment),
        ("Setup database", setup_database),
        ("Run migrations", run_migrations),
        ("Generate sample data", generate_sample_data),
    ]
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        if not step_func():
            print(f"\n❌ Setup failed at step: {step_name}")
            print("Please fix the errors and run the setup again.")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ Project setup completed successfully!")
    print("\n📖 Next steps:")
    print("   1. Update your .env file with proper configuration")
    print("   2. Start the FastAPI server:")
    if sys.platform.startswith('win'):
        print("      .venv\\Scripts\\activate")
    else:
        print("      source .venv/bin/activate")
    print("      cd backend")
    print("      uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print("   3. Access the API at http://localhost:8000")
    print("   4. View API docs at http://localhost:8000/docs")
    print("   5. Access PgAdmin at http://localhost:5050 (admin@healthcare.com / admin)")
    print("\n🎉 Happy coding!")

if __name__ == "__main__":
    main()