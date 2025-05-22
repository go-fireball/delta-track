# Portfolio Tracker

This project is a portfolio tracking application.

## Project Setup

This project uses Python and [Poetry](https://python-poetry.org/) for dependency management.

1.  **Install Poetry:**
    If you don't have Poetry installed, follow the instructions on the [official Poetry website](https://python-poetry.org/docs/#installation).

2.  **Install Dependencies:**
    Navigate to the project root directory and run:
    ```bash
    poetry install
    ```

## Database Setup

The application uses a PostgreSQL database.

1.  **Ensure PostgreSQL is Running:**
    Make sure you have a PostgreSQL instance running and accessible.

2.  **Configure Connection:**
    The database connection is configured using the following environment variables. If these are not set, default values will be used.

    - `POSTGRES_USER`: The PostgreSQL username (default: `user`)
    - `POSTGRES_PASSWORD`: The PostgreSQL password (default: `password`)
    - `POSTGRES_HOST`: The host of the PostgreSQL server (default: `localhost`)
    - `POSTGRES_PORT`: The port of the PostgreSQL server (default: `5432`)
    - `POSTGRES_DB`: The name of the database to use (default: `portfolio`)

    You can set these environment variables in your shell or using a `.env` file (though note that this project does not automatically load `.env` files; you would need to source it manually or use a library like `python-dotenv` if desired).

3.  **Create Database Tables:**
    Once the environment variables are set (if you're not using the defaults), run the following script from the project root to create the necessary database tables:
    ```bash
    python create_db.py
    ```
    You should see a message "Database tables created successfully."
