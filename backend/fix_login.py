import mysql.connector
import bcrypt

# Connect to MySQL
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='password',
    database='librarypro'
)
cur = conn.cursor()

# Generate proper hash
h = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode()

# Delete old broken admin and re-insert with correct hash
cur.execute("DELETE FROM users WHERE username='admin'")
cur.execute("""
    INSERT INTO users (username, password_hash, role, full_name, email, is_vip)
    VALUES ('admin', %s, 'admin', 'Library Admin', 'admin@lib.com', 0)
""", (h,))

# Also fix student
h2 = bcrypt.hashpw(b'student123', bcrypt.gensalt()).decode()
cur.execute("DELETE FROM users WHERE username='john_doe'")
cur.execute("""
    INSERT INTO users (username, password_hash, role, full_name, email, is_vip)
    VALUES ('john_doe', %s, 'student', 'John Doe', 'john@student.com', 0)
""", (h2,))

conn.commit()
cur.close()
conn.close()

print("All done!")
print("Login: admin / admin123")
print("Login: john_doe / student123")
