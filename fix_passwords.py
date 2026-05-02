import bcrypt
import MySQLdb

try:
    db = MySQLdb.connect(host="localhost", user="root", passwd="", db="smart_watch_db", charset="utf8mb4")
    cur = db.cursor()

    hashed = bcrypt.hashpw('Admin@123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    cur.execute("UPDATE users SET password_hash = %s", (hashed,))
    db.commit()
    cur.close()
    db.close()
    print("Passwords fixed successfully!")
except Exception as e:
    print(f"Error: {e}")
