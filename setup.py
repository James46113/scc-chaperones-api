from app import db, app
import subprocess
import os


def shell(command):
    result = subprocess.run(command, shell=True,
                            capture_output=True, text=True)
    print(command)
    if result.returncode != 0:
        raise Exception(
            f"Command '{command}' failed with error: {result.stderr}")
    return result.stdout


if __name__ == "__main__":
    with app.app_context():
        # Check if the migrations directory exists
        if not os.path.exists('migrations'):
            shell("flask db init")

        # Create all tables
        db.create_all()

        # Generate a new migration script
        shell("flask db migrate")

        # Apply the migrations
        shell("flask db upgrade")
