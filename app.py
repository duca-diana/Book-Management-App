from flask import Flask, render_template, request, redirect, url_for
from models import connectDB , createTables
from flask_login import LoginManager, current_user, login_user, UserMixin, login_required, logout_user
from forms import RegistrationForm, LoginForm
from flask import flash
import requests
import os
import bcrypt
from datetime import datetime

secret_key = os.urandom(24)

app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

@app.route('/')
def index():
    createTables()
    conn = connectDB()
    cursor = conn.cursor()
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    else:

        cursor.execute('SELECT * FROM books')
        books = cursor.fetchall()

    conn.close()

    return render_template('index.html', books=books)



@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        conn = connectDB()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[2]): 
            user_id = user[0]
            user = User(user_id)
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed. Please check your credentials.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html', title='Login', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        confirm_password = form.confirm_password.data

        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'error')
            return render_template('register.html', title='Register', form=form)

        try:
            db = connectDB()
            cursor = db.cursor()

            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash('Username already exists. Please choose a different one.', 'error')
                return render_template('register.html', title='Register', form=form)

            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            db.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('An error occurred during registration. Please try again later.', 'error')
            print(e)
        finally:
            db.close()

    return render_template('register.html', title='Register', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@login_manager.user_loader
def load_user(user_id):
    return User(user_id) 

@app.route('/search_books', methods=['POST'])
def search_books():
    query = request.form.get('search_query')

    api_key = 'AIzaSyDB4hYF2AAQyldpPl3aLyK-TSmxotdm9_Q'
    url = f'https://www.googleapis.com/books/v1/volumes?q={query}&key={api_key}'

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()


        books = []
        for item in data.get('items', []):
            volume_info = item.get('volumeInfo', {})

            book = {
                'title': volume_info.get('title', 'N/A'),
                'author': ', '.join(volume_info.get('authors', ['N/A'])),
                'genre': ', '.join(volume_info.get('categories', ['N/A'])),
                'description': volume_info.get('description', 'N/A'),
                'cover_image': volume_info.get('imageLinks', {}).get('thumbnail', 'N/A'),
                'isbn': volume_info.get('industryIdentifiers', [{'type': 'ISBN_13', 'identifier': 'N/A'}])[0]['identifier'],
                'publication_date': volume_info.get('publishedDate', 'N/A'),
            }

            books.append(book)

        return render_template('search_results.html', books=books)
    else:
        return 'Failed to retrieve book data from Google Books API'


@app.route('/collection')
@login_required
def collection():
    conn = connectDB()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT b.* FROM books AS b
        JOIN userbooks AS ub ON b.book_id = ub.book_id
        WHERE ub.user_id = ?
    ''', (current_user.id,))
    collection = cursor.fetchall()

    conn.close()

    return render_template('collection.html', collection=collection)


@app.route('/add_from_search', methods=['POST'])
@login_required
def add_from_search():
    title = request.form.get('title')
    author = request.form.get('author')
    genre = request.form.get('genre')
    description = request.form.get('description')
    cover_image = request.form.get('cover_image')
    isbn = request.form.get('isbn')
    publication_date = request.form.get('publication_date')

    try:
        db = connectDB()
        cursor = db.cursor()

        cursor.execute('SELECT book_id FROM books WHERE isbn = ?', (isbn,))
        existing_book = cursor.fetchone()

        if not existing_book:
            cursor.execute('''
                INSERT INTO books (title, author, genre, description, cover_image, isbn, publication_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, author, genre, description, cover_image, isbn, publication_date))
            db.commit()

            cursor.execute('SELECT book_id FROM books WHERE isbn = ?', (isbn,))
            book_id = cursor.fetchone()[0]

        else:
            book_id = existing_book[0]

        cursor.execute('''
            INSERT INTO userbooks (user_id, book_id, ownership_date)
            VALUES (?, ?, ?)
        ''', (current_user.id, book_id, datetime.now()))
        db.commit()
        print("Book added to the user's collection successfully!")

    except:
        print("Failed to add the book to the user's collection!")

    finally:
        db.close()

    return redirect(url_for('index'))


@app.route('/delete_book', methods=['POST'])
@login_required
def delete_book():
    isbn = request.form.get('isbn')

    try:
        db = connectDB()
        cursor = db.cursor()

        cursor.execute('''
            SELECT b.book_id
            FROM books AS b
            JOIN userbooks AS ub ON b.book_id = ub.book_id
            WHERE ub.user_id = ? AND b.isbn = ?
        ''', (current_user.id, isbn))
        book_id = cursor.fetchone()

        if book_id:
            cursor.execute('DELETE FROM userbooks WHERE user_id = ? AND book_id = ?', (current_user.id, book_id[0]))
            db.commit()
            print("Book removed from the user's collection successfully!")
        else:
            print("Book does not exist in the user's collection!")

    except:
        print("Failed to remove the book from the user's collection!")

    finally:
        db.close()

    return redirect(url_for('collection'))


if __name__ == '__main__':
    createTables()
    conn = connectDB()
    cursor = conn.cursor()
    app.run(debug=True)