import os
import sys
import subprocess
import webbrowser
import time
import threading

def run():
    print("========================================")
    print("  MediCart - Startup and Setup Script  ")
    print("========================================")

    # 1. Determine venv structure
    venv_dir = '.venv'
    if os.name == 'nt':
        pip_path = os.path.join(venv_dir, 'Scripts', 'pip.exe')
        python_path = os.path.join(venv_dir, 'Scripts', 'python.exe')
    else:
        pip_path = os.path.join(venv_dir, 'bin', 'pip')
        python_path = os.path.join(venv_dir, 'bin', 'python')

    # 2. Create virtual environment if it doesn't exist
    if not os.path.exists(venv_dir):
        print(f"Creating virtual environment in {venv_dir}...")
        try:
            subprocess.run([sys.executable, '-m', 'venv', venv_dir], check=True)
            print("Virtual environment created successfully.")
        except Exception as e:
            print(f"Error creating virtual environment: {e}")
            sys.exit(1)

    # 3. Install requirements
    if os.path.exists('requirements.txt'):
        print("Installing requirements from requirements.txt...")
        try:
            subprocess.run([pip_path, 'install', '--upgrade', 'pip'], check=True)
            subprocess.run([pip_path, 'install', '-r', 'requirements.txt'], check=True)
            print("Dependencies installed successfully.")
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            sys.exit(1)
    else:
        print("requirements.txt not found. Skipping dependency installation.")

    # 4. Run Django migrations
    print("Running database migrations...")
    try:
        subprocess.run([python_path, 'manage.py', 'makemigrations'], check=True)
        subprocess.run([python_path, 'manage.py', 'migrate'], check=True)
        print("Database migrated successfully.")
    except Exception as e:
        print(f"Error running migrations: {e}")
        sys.exit(1)

    # 5. Populate database
    if os.path.exists('populate_db.py'):
        print("Seeding database with medicine inventory, interactions, and categories...")
        try:
            subprocess.run([python_path, 'populate_db.py'], check=True)
            print("Database seeded successfully.")
        except Exception as e:
            print(f"Error seeding database: {e}")
            # Non-blocking: continue even if seeding fails
    else:
        print("populate_db.py not found. Skipping seeding.")

    # 6. Open Web Browser
    def open_browser():
        time.sleep(2.5)
        print("\n[Browser] Opening http://127.0.0.1:8000/ in browser...")
        webbrowser.open("http://127.0.0.1:8000/")

    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()

    # 7. Start Django Server
    print("Starting Django development server...")
    try:
        subprocess.run([python_path, 'manage.py', 'runserver', '127.0.0.1:8000'], check=True)
    except KeyboardInterrupt:
        print("\nStopping server...")
    except Exception as e:
        print(f"Error launching server: {e}")

if __name__ == '__main__':
    run()
