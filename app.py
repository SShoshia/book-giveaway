import os
from flask import Flask, jsonify, request, redirect, url_for, render_template, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from models import db, User, Book, UserBookInterest

app = Flask(__name__)
app.secret_key = os.urandom(24)

# configure database for app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# used for hashing passwords
bcrypt = Bcrypt()

# create tables if not done already
with app.app_context():
    db.create_all()

# initialize flask login
login_manager = LoginManager()
login_manager.init_app(app)

# user loader
@login_manager.user_loader
def load_user(user_id):
    u = User.query.get(user_id)
    return u

@app.route('/')
def slash():
    # simple redirect
    return redirect(url_for('home'))

@app.route('/home', methods=['GET', 'POST'])
def home():
    # filtering options
    author = request.args.get('author')
    genre = request.args.get('genre')

    filtered_books = Book.query

    # filter if options provided
    if author:
        filtered_books = filtered_books.filter(Book.author.ilike(f"%{author}%"))

    if genre:
        filtered_books = filtered_books.filter(Book.genre.ilike(f"%{genre}%"))

    filtered_books = filtered_books.all()

    return render_template('home.html', filtered_books=filtered_books)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        # check if the username or email is already in use
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already in use. Please choose a different username.', 'danger')
            return redirect(url_for('register'))

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already in use. Please use a different email address.', 'danger')
            return redirect(url_for('register'))

        # create a new user
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. You can now log in.', 'success')
        return redirect(url_for('login'))
    
    # for the GET request
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        # username exists and password is correct
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Please check your username and password.', 'danger')
    
    # for the GET request
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    # get books owned by the logged in user
    user_books = Book.query.filter_by(owner_id=current_user.id).all()
    return render_template('dashboard.html', user_books=user_books)

@app.route('/books', methods=['POST'])
@login_required
def create_book():
    data = request.get_json()
    title = data.get('title')
    author = data.get('author')
    genre = data.get('genre')
    condition = data.get('condition')
    location = data.get('location')

    book = Book(title=title, author=author, genre=genre, condition=condition, location=location, owner_id=current_user.id)
    db.session.add(book)
    db.session.commit()
    
    return jsonify(message='Book created successfully')

@app.route('/manage_book', methods=['GET', 'POST'])
@app.route('/manage_book/<int:book_id>', methods=['GET', 'POST'])
@login_required
def manage_book(book_id=None):
    if book_id is None:
        book = None
    else:
        book = Book.query.get_or_404(book_id)

    if request.method == 'POST':
        # POST request: edit/create book
        title = request.form['title']
        author = request.form['author']
        genre = request.form['genre']
        condition = request.form['condition']
        location = request.form['location']

        if book is None:
            # create a new book
            new_book = Book(title=title, author=author, genre=genre, condition=condition, location=location, owner_id=current_user.id)
            db.session.add(new_book)
            flash('Book added successfully.', 'success')
        else:
            # update an existing book
            book.title = title
            book.author = author
            book.genre = genre
            book.condition = condition
            book.location = location
            flash('Book updated successfully.', 'success')

        db.session.commit()
        return redirect(url_for('dashboard'))

    # GET request: display the template for editing/creating a book
    return render_template('manage_book.html', book=book)

@app.route('/delete_book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    if str(book.owner_id).strip() != str(current_user.id).strip():
        flash('You do not have permission to delete this book.', 'danger')
        return redirect(url_for('dashboard'))

    db.session.delete(book)
    db.session.commit()
    flash('Book deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/update_interest', methods=['POST'])
def update_interest():
    if request.method == 'POST':
        book_ids = request.form.getlist('interests')
        user_id = current_user.id

        UserBookInterest.query.filter_by(user_id=user_id).delete()

        for book_id in book_ids:
            interest = UserBookInterest(user_id=user_id, book_id=book_id)
            db.session.add(interest)

        db.session.commit()
        flash('Interests updated successfully', 'success')
        return redirect(url_for('home'))

@app.route('/view_interested_users/<int:book_id>', methods=['GET', 'POST'])
def view_interested_users(book_id):
    book = Book.query.get_or_404(book_id)
    interested_users = User.query.join(UserBookInterest).filter(UserBookInterest.book_id == book_id).all()

    if request.method == 'POST':
        selected_user_id = request.form.get('selected_user')
        if selected_user_id:
            selected_user = User.query.get(selected_user_id)
            # transfer ownership of the book to the selected user
            book.owner_id = selected_user.id
            # remove the selected user's interest from the book
            UserBookInterest.query.filter_by(user_id=selected_user.id, book_id=book.id).delete()

            db.session.commit()

            flash('Book ownership updated successfully', 'success')
            return redirect(url_for('dashboard'))

    return render_template('view_interested_users.html', book=book, interested_users=interested_users)


if __name__ == '__main__':
    app.run(debug=True)
