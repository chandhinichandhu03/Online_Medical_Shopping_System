# MediCart - Advanced Online Medical Shopping System

An advanced medical commerce and healthcare system featuring local RAG (Retrieval-Augmented Generation) symptom analysis, prescription OCR reading, smart drug interaction graphs, ML inventory/demand forecasting, blockchain batch tracking, user health profiles, and multi-role workflows.

## How to Run (Windows & macOS)

You can set up, seed, and run the entire application using a single cross-platform script:

1. Open your terminal or command prompt in this directory.
2. Run the following command:
   ```bash
   python run.py
   ```

The script will automatically:
- Create a Python virtual environment (`.venv`).
- Install all requirements.
- Run database migrations.
- Seed database records (medicines, ingredients, batch data, categories).
- Launch the development server and open the store in your default browser.

---

## One-Liner Startup Command (Alternative)

If you want to run the setup and start the server using a single inline command copy-pasted into your terminal:

### macOS / Linux (Terminal)
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python3 manage.py migrate && python3 populate_db.py && python3 manage.py runserver
```

### Windows (PowerShell)
```powershell
python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -r requirements.txt; python manage.py migrate; python populate_db.py; python manage.py runserver
```

---

## Complete Runner Script Source Code (`run.py`)

Here is the complete code of the cross-platform startup runner script `run.py` for reference:

```python
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
```

