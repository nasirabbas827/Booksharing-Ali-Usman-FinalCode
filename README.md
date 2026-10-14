# Booksharing Ali Usman Final Code

Booksharing-Ali-Usman-FinalCode is a community book-sharing application.

![Flask](https://img.shields.io/badge/Flask-2563EB?style=flat-square) ![SQLite](https://img.shields.io/badge/SQLite-0F172A?style=flat-square)

## Overview

The data model covers `UserStatus`, `BorrowStatus`, `User`, `Category`, `Book`, `BorrowRequest`, `Message`, `Admin`.

## Implemented workflows

The source defines these handlers:

- **Index** — `index`
- **Register** — `register`
- **Login** — `login`
- **Dashboard** — `dashboard`
- **Update Profile** — `update_profile`
- **Logout** — `logout`
- **Categories** — `categories`
- **Category Form** — `category_form`
- **Delete Category** — `delete_category`
- **Books** — `books`
- **Book Form** — `book_form`
- **Delete Book** — `delete_book`

## Getting started

### 1. Get the project

```bash
git clone https://github.com/nasirabbas827/Booksharing-Ali-Usman-FinalCode.git
cd Booksharing-Ali-Usman-FinalCode
```

### 2. Prepare Python

Create an isolated environment:

```bash
python -m venv .venv
```

Activate it with `.venv\Scripts\activate` on Windows Command Prompt, or `source .venv/bin/activate` on macOS/Linux.

No requirements file is included. The inspected Python imports indicate these dependencies as a starting point:

```bash
python -m pip install Flask Flask-Login Werkzeug Flask-SQLAlchemy
```

Dependency versions are not pinned in this repository.

### 3. Configure and run

Keep the included SQLite database files in their expected locations: [`instance/book_sharing.db`](instance/book_sharing.db).

Run from the repository root so relative file paths resolve correctly:

```bash
python app.py
```

Open http://127.0.0.1:5000/, or use the address printed by the application.

## Repository guide

| Path | Purpose |
| --- | --- |
| [`app.py`](app.py) | Application entry point |
| [`instance`](instance) | Local Flask instance data |
| [`static`](static) | Static application assets |
| [`templates`](templates) | HTML page templates |

## Development notes

These setup instructions are based on the repository source. The application has not been executed as part of this documentation update; verify dependencies and configuration in your local environment.
