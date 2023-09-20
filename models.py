import sqlite3 as lit

def connectDB():
    return lit.connect('inventory.db')

def createTables():
    try:
        db=connectDB()
        cursor = db.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                book_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT,
                description TEXT,
                cover_image TEXT,
                isbn TEXT,
                publication_date TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS userbooks (
                userbook_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                book_id INTEGER,
                ownership_date TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (book_id) REFERENCES books (book_id)
            )
        ''')

        db.commit()
        print("Database created succesfully!")
    except:
        print("Failed to create the DataBase!")

    finally:
        db.close()
