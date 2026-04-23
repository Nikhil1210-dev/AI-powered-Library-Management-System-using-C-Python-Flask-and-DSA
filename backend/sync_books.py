import mysql.connector
import os

# Connect to MySQL
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='password',
    database='librarypro'
)
cur = conn.cursor(dictionary=True)
cur.execute("SELECT * FROM books")
books = cur.fetchall()
cur.close()
conn.close()

# Write to library_data.dat (C++ engine format)
dat_file = os.path.join(os.path.dirname(__file__), 'library_data.dat')

with open(dat_file, 'w') as f:
    for b in books:
        # Format: id|title|author|category|issued|student_name|student_id|due_date|vip
        f.write(f"{b['id']}|{b['title']}|{b['author']}|{b['category']}|0|-|-|-|0\n")

print(f"Synced {len(books)} books to library_data.dat")
for b in books:
    print(f"  #{b['id']} — {b['title']}")
