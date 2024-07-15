import sqlite3
from sqlite3 import Error

class DatabaseManager:
    def __init__(self, db_file):
        """Initialize the database manager with the database file path."""
        self.db_file = db_file
        self.conn = None

    def create_connection(self):
        """Create a database connection to the SQLite database specified by db_file."""
        try:
            self.conn = sqlite3.connect(self.db_file)
            print(f"Connection to {self.db_file} established.")
        except Error as e:
            print(f"Error connecting to database: {e}")

    def close_connection(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

    def execute_query(self, query, params=None):
        """Execute a single query with optional parameters."""
        try:
            cur = self.conn.cursor()
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            self.conn.commit()
            print("Query executed successfully.")
        except Error as e:
            print(f"Error executing query: {e}")

    def fetch_all(self, query, params=None):
        """Fetch all results from a query with optional parameters."""
        try:
            cur = self.conn.cursor()
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            rows = cur.fetchall()
            return rows
        except Error as e:
            print(f"Error fetching data: {e}")
            return []

    def fetch_one(self, query, params=None):
        """Fetch a single result from a query with optional parameters."""
        try:
            cur = self.conn.cursor()
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            row = cur.fetchone()
            return row
        except Error as e:
            print(f"Error fetching data: {e}")
            return None