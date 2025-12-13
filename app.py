"""
Book Sharing Platform - Flask Application

A simple web application for users to register, share books (physical or digital),
categorize them, search for books owned by others, send borrow requests,
communicate via messages, and manage their profile and listings.

Features:
- User authentication (register, login, logout, profile update)
- Book management (add, edit, delete own books)
- Category management
- Borrow request workflow (send, view incoming, accept/reject/counter-propose)
- Messaging between borrower and owner
- File uploads for profile pictures and digital books
"""

from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Category, Book, BorrowRequest, Message, UserStatus, Admin
import os

# ========================
# Application Configuration
# ========================
app = Flask(__name__)

app.config['SECRET_KEY'] = 'dev-secret-key'  # Change this in production!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///book_sharing.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/profile_pictures'

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/uploads/books', exist_ok=True)

# Initialize extensions
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect unauthenticated users to login page


# ========================
# User Loader for Flask-Login (SINGLE, CORRECT VERSION)
# ========================
# ========================
# User Loader for Flask-Login (SAFE VERSION)
# ========================
@login_manager.user_loader
def load_user(user_id):
    """
    Safely load either a regular User or Admin.
    Regular users have normal auto-increment IDs (1, 2, 3...).
    Admin uses fixed high ID (999999) → no collision possible.
    """
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None

    # First: Try to load as regular User (most common case)
    user = User.query.get(uid)
    if user:
        return user

    # Second: Only check for Admin if the ID is the known admin ID
    if uid == 999999:
        return Admin.query.get(uid)

    # No match
    return None

# ========================
# Home / Index Route
# ========================
@app.route('/')
def index():
    """Render the landing/home page."""
    return render_template('index.html')


# ========================
# User Registration
# ========================
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration (GET: show form, POST: process submission)."""
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        full_name = request.form.get('full_name', '').strip()
        location = request.form.get('location', '').strip()

        # Check if username or email already exists
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists', 'error')
            return redirect(url_for('register'))

        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            location=location
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# ========================
# User Login
# ========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login (GET: show form, POST: authenticate)."""
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        # Invalid email
        if not user:
            flash('Invalid credentials', 'error')
            return redirect(url_for('login'))

        # Blocked account
        if user.status != UserStatus.unblocked:
            flash('Your account is blocked. Contact administrator.', 'error')
            return redirect(url_for('login'))

        # Wrong password
        if not check_password_hash(user.password_hash, password):
            flash('Invalid credentials', 'error')
            return redirect(url_for('login'))

        # Successful login
        login_user(user)
        flash('Login successful', 'success')
        return redirect(url_for('dashboard'))

    return render_template('login.html')


# ========================
# User Dashboard
# ========================
@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard for authenticated users."""
    my_books = Book.query.filter_by(owner_id=current_user.id).order_by(Book.title).all()
    
    incoming_requests = BorrowRequest.query.filter_by(owner_id=current_user.id)\
                                           .order_by(BorrowRequest.created_at.desc()).all()
    
    outgoing_requests = BorrowRequest.query.filter_by(borrower_id=current_user.id)\
                                           .order_by(BorrowRequest.created_at.desc()).all()

    return render_template(
        'dashboard.html',
        my_books=my_books,
        incoming_requests=incoming_requests,
        outgoing_requests=outgoing_requests
    )

# ========================
# Update Profile
# ========================
@app.route('/update-profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    """Allow users to update their profile information and picture."""
    if request.method == 'POST':
        # Update basic fields
        current_user.username = request.form['username'].strip()
        current_user.email = request.form['email'].strip().lower()
        current_user.full_name = request.form.get('full_name', '').strip()
        current_user.location = request.form.get('location', '').strip()

        # Optional password change
        new_password = request.form.get('password')
        if new_password:
            current_user.password_hash = generate_password_hash(new_password)

        # Profile picture upload
        file = request.files.get('profile_picture')
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            current_user.profile_picture = f'uploads/profile_pictures/{filename}'

        db.session.commit()
        flash('Profile updated successfully', 'success')

    return render_template('update_profile.html')


# ========================
# Logout
# ========================
@app.route('/logout')
@login_required
def logout():
    """Log the current user out and redirect to login."""
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))


# ========================
# Category Management
# ========================
@app.route('/categories')
@login_required
def categories():
    """Display all book categories."""
    all_categories = Category.query.order_by(Category.name).all()
    return render_template('categories.html', categories=all_categories)


@app.route('/category', methods=['GET', 'POST'])
@app.route('/category/<int:id>', methods=['GET', 'POST'])
@login_required
def category_form(id=None):
    """Add new category or edit existing one."""
    category = Category.query.get_or_404(id) if id else None

    if request.method == 'POST':
        name = request.form['name'].strip()

        if not name:
            flash('Category name is required', 'error')
            return redirect(request.url)

        # Prevent duplicate category names
        existing = Category.query.filter_by(name=name).first()
        if existing and (category is None or existing.id != category.id):
            flash('Category name already exists', 'error')
            return redirect(request.url)

        if category:
            category.name = name
            flash('Category updated successfully', 'success')
        else:
            category = Category(name=name)
            db.session.add(category)
            flash('Category added successfully', 'success')

        db.session.commit()
        return redirect(url_for('categories'))

    return render_template('category_form.html', category=category)


@app.route('/category/delete/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    """Delete a category (only if no books are associated - handled by DB constraints)."""
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully', 'success')
    return redirect(url_for('categories'))


# ========================
# Book Management (User's Own Books)
# ========================
@app.route('/books')
@login_required
def books():
    """List all books owned by the current user."""
    user_books = Book.query.filter_by(owner_id=current_user.id).order_by(Book.title).all()
    return render_template('books.html', books=user_books)


@app.route('/book', methods=['GET', 'POST'])
@app.route('/book/<int:id>', methods=['GET', 'POST'])
@login_required
def book_form(id=None):
    """Add a new book or edit an existing one owned by the user."""
    book = Book.query.get(id) if id else None
    categories = Category.query.order_by(Category.name).all()

    # Prevent editing someone else's book
    if book and book.owner_id != current_user.id:
        flash("You can only edit your own books", "error")
        return redirect(url_for('books'))

    if request.method == 'POST':
        title = request.form['title'].strip()
        author = request.form['author'].strip()
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category_id')
        book_type = request.form.get('book_type')  # 'physical' or 'digital'
        status = request.form.get('status', 'available')
        physical_location = request.form.get('physical_location') if book_type == 'physical' else None
        download_link = request.form.get('download_link') if book_type == 'digital' else None

        # Handle digital file upload
        file_path = None
        file = request.files.get('file_path')
        if file and file.filename and book_type == 'digital':
            filename = secure_filename(file.filename)
            full_path = os.path.join('static/uploads/books', filename)
            file.save(full_path)
            file_path = f'uploads/books/{filename}'

        if book:
            # Update existing book
            book.title = title
            book.author = author
            book.description = description
            book.category_id = category_id
            book.book_type = book_type
            book.status = status
            book.physical_location = physical_location
            book.download_link = download_link
            if file_path:
                book.file_path = file_path
            flash("Book updated successfully", "success")
        else:
            # Create new book
            new_book = Book(
                owner_id=current_user.id,
                title=title,
                author=author,
                description=description,
                category_id=category_id,
                book_type=book_type,
                status=status,
                physical_location=physical_location,
                download_link=download_link,
                file_path=file_path
            )
            db.session.add(new_book)
            flash("Book added successfully", "success")

        db.session.commit()
        return redirect(url_for('books'))

    return render_template('book_form.html', book=book, categories=categories)


@app.route('/book/delete/<int:id>', methods=['POST'])
@login_required
def delete_book(id):
    """Delete a book owned by the current user."""
    book = Book.query.get_or_404(id)
    if book.owner_id != current_user.id:
        flash("You can only delete your own books", "error")
        return redirect(url_for('books'))

    db.session.delete(book)
    db.session.commit()
    flash("Book deleted successfully", "success")
    return redirect(url_for('books'))


# ========================
# Search & Borrow Requests
# ========================
@app.route('/search-books', methods=['GET', 'POST'])
@login_required
def search_books():
    """Search for books owned by other users (exclude own books)."""
    query = request.args.get('query', '').strip()
    category_id = request.args.get('category_id', type=int)  # None if empty or invalid

    # Base query: only available books not owned by current user
    books_query = Book.query.filter(
        Book.owner_id != current_user.id,
        Book.status == 'available'
    )

    if query:
        search_pattern = f"%{query}%"
        books_query = books_query.filter(
            (Book.title.ilike(search_pattern)) | (Book.author.ilike(search_pattern))
        )

    if category_id is not None:  # Only filter if a valid category was selected
        books_query = books_query.filter_by(category_id=category_id)

    books = books_query.order_by(Book.title).all()
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        'search_books.html',
        books=books,
        categories=categories,
        query=query,
        selected_category=category_id  # Will be None or int → safe for comparison
    )

@app.route('/borrow-request/<int:book_id>', methods=['GET', 'POST'])
@login_required
def borrow_request_form(book_id):
    book = Book.query.get_or_404(book_id)

    if book.owner_id == current_user.id:
        flash("You cannot borrow your own book.", "error")
        return redirect(url_for('search_books'))

    if request.method == 'POST':
        proposed_date = request.form.get('proposed_date')
        proposed_time = request.form.get('proposed_time')
        proposed_location = request.form.get('proposed_location')

        # Basic validation
        if not all([proposed_date, proposed_time, proposed_location]):
            flash("Please fill in all fields.", "error")
            return redirect(request.url)

        borrow_req = BorrowRequest(
            book_id=book.id,
            borrower_id=current_user.id,
            owner_id=book.owner_id,
            proposed_date=proposed_date,        # String: "2025-12-14"
            proposed_time=proposed_time,        # String: "14:30"
            proposed_location=proposed_location,
            status='pending'
        )
        db.session.add(borrow_req)
        db.session.commit()
        flash("Borrow request sent successfully!", "success")
        return redirect(url_for('search_books'))

    return render_template('borrow_request_form.html', book=book)

# ========================
# Owner: Incoming Borrow Requests
# ========================
@app.route('/incoming-requests')
@login_required
def incoming_requests():
    """Show all borrow requests received by the current user (book owner)."""
    requests = BorrowRequest.query.filter_by(owner_id=current_user.id)\
                                  .order_by(BorrowRequest.created_at.desc()).all()
    return render_template('incoming_requests.html', requests=requests)


@app.route('/update-borrow-request/<int:request_id>', methods=['GET', 'POST'])
@login_required
def update_borrow_request(request_id):
    """Allow book owner to accept, reject, or counter-propose a borrow request."""
    borrow_req = BorrowRequest.query.get_or_404(request_id)

    if borrow_req.owner_id != current_user.id:
        flash("Unauthorized access.", "error")
        return redirect(url_for('incoming_requests'))

    if request.method == 'POST':
        action = request.form.get('status')
        if action in ['accepted', 'rejected', 'modified']:
            borrow_req.status = action
        borrow_req.owner_proposed_date = request.form.get('owner_proposed_date')
        borrow_req.owner_proposed_time = request.form.get('owner_proposed_time')
        db.session.commit()
        flash("Borrow request updated.", "success")
        return redirect(url_for('incoming_requests'))

    return render_template('update_borrow_request.html', borrow_req=borrow_req)


# ========================
# Borrower: View Borrowed Books / Requests
# ========================
@app.route('/borrowed-books')
@login_required
def borrowed_books():
    """Show all borrow requests made by the current user."""
    requests = BorrowRequest.query.filter_by(borrower_id=current_user.id)\
                                  .order_by(BorrowRequest.created_at.desc()).all()
    return render_template('borrowed_books.html', requests=requests)



# ========================
# Mark Borrow Request as Returned (by Borrower)
# ========================
@app.route('/mark-returned/<int:request_id>', methods=['POST'])
@login_required
def mark_as_returned(request_id):
    """Allow the borrower to mark a borrow request as 'returned' when status is 'accepted'."""
    borrow_req = BorrowRequest.query.get_or_404(request_id)

    # Security checks
    if borrow_req.borrower_id != current_user.id:
        flash("You can only mark your own borrow requests as returned.", "error")
        return redirect(url_for('borrowed_books'))

    if borrow_req.status.value != 'accepted':
        flash("You can only mark an accepted request as returned.", "error")
        return redirect(url_for('borrowed_books'))

    from models import BorrowStatus  # or import at top
    borrow_req.status = BorrowStatus.returned
    db.session.commit()

    flash(f'You have successfully marked "{borrow_req.book.title}" as returned.', "success")
    return redirect(url_for('borrowed_books'))

# ========================
# Messaging Between Borrower and Owner
# ========================
@app.route('/messages/<int:borrow_request_id>', methods=['GET', 'POST'])
@login_required
def messages(borrow_request_id):
    """View and send messages related to a specific borrow request."""
    borrow_req = BorrowRequest.query.get_or_404(borrow_request_id)

    # Ensure only owner or borrower can access
    if current_user.id not in (borrow_req.owner_id, borrow_req.borrower_id):
        flash("Unauthorized access.", "error")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        msg_text = request.form.get('message', '').strip()
        if msg_text:
            receiver_id = borrow_req.owner_id if current_user.id == borrow_req.borrower_id else borrow_req.borrower_id
            message = Message(
                sender_id=current_user.id,
                receiver_id=receiver_id,
                borrow_request_id=borrow_request_id,
                message=msg_text
            )
            db.session.add(message)
            db.session.commit()
            flash("Message sent.", "success")

        return redirect(url_for('messages', borrow_request_id=borrow_request_id))

    messages_list = Message.query.filter_by(borrow_request_id=borrow_request_id)\
                                 .order_by(Message.created_at.asc()).all()

    return render_template('messages.html', borrow_req=borrow_req, messages=messages_list)


# -------------------------
# Admin Login
# -------------------------
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admin = Admin.query.filter_by(username=username).first()
        if not admin or admin.password != password: 
            flash('Access denied', 'error')
            return redirect(url_for('admin_login'))

        login_user(admin)
        flash('Admin login successful', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_login.html')


# -------------------------
# Admin Dashboard
# -------------------------
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    books = Book.query.all()
    users = User.query.all()
    return render_template('admin_dashboard.html', books=books, users=users)


# -------------------------
# Admin Actions
# -------------------------
@app.route('/admin/block_user/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)
    user.status = UserStatus.blocked
    db.session.commit()
    flash(f'User {user.username} blocked successfully', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/unblock_user/<int:user_id>', methods=['POST'])
@login_required
def unblock_user(user_id):
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)
    user.status = UserStatus.unblocked
    db.session.commit()
    flash(f'User {user.username} unblocked successfully', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete_book/<int:book_id>', methods=['POST'])
@login_required
def admin_delete_book(book_id):
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash(f'Book "{book.title}" deleted successfully', 'success')
    return redirect(url_for('admin_dashboard'))


# -------------------------
# Admin Logout
# -------------------------
@app.route('/admin/logout')
@login_required
def admin_logout():
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        return redirect(url_for('index'))
    logout_user()
    flash('Admin logged out', 'success')
    return redirect(url_for('admin_login'))


# ========================
# Application Entry Point
# ========================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        Admin.create_default_admin()  # Ensure default admin exists (username: admin, password: admin)
    app.run(debug=True)