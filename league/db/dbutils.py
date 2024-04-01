# People should be able to upload files with strategies
# Once a strategy is uploaded, main.py will trigger a simutils function to run the simulations
# In front it will be shown (thanks to flask) the current state of the league
import sqlite3

class DBUtils:
    def __init__(self, db_name='database.db'):
        self.db_name = db_name
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.create_tables()

    def create_tables(self):
        if self.conn is not None:
            cursor = self.conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS USERS (
                                username TEXT PRIMARY KEY
                            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS AGENT (
                                filename TEXT PRIMARY KEY,
                                agent_name TEXT
                            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS MATCH (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                agent1_filename TEXT,
                                agent1_name TEXT,
                                agent2_filename TEXT,
                                agent2_name TEXT,
                                nwins_player1 INTEGER,
                                nwins_player2 INTEGER,
                                FOREIGN KEY (agent1_filename, agent1_name) REFERENCES AGENT(filename, agent_name),
                                FOREIGN KEY (agent2_filename, agent2_name) REFERENCES AGENT(filename, agent_name)
                            )''')
            self.conn.commit()

    def add_user(self, username):
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute("INSERT INTO USERS (username) VALUES (?)", (username,))
                self.conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def add_agent(self, filename, agent_name):
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute("INSERT INTO AGENT (filename, agent_name) VALUES (?, ?)", (filename, agent_name))
                self.conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def add_match_result(self, agent1_filename, agent1_name, agent2_filename, agent2_name, nwins_player1, nwins_player2):
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute("INSERT INTO MATCH (agent1_filename, agent1_name, agent2_filename, agent2_name, nwins_player1, nwins_player2) VALUES (?, ?, ?, ?, ?, ?)",
                               (agent1_filename, agent1_name, agent2_filename, agent2_name, nwins_player1, nwins_player2))
                self.conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_matches(self):
        matches = {}
        if self.conn is not None:
            cursor = self.conn.cursor()

            # Query for matches involving agent1
            cursor.execute("SELECT agent1_filename, agent1_name, nwins_player1 FROM MATCH")
            rows = cursor.fetchall()
            for row in rows:
                filename = row[0]
                agent_name = row[1]
                wins = row[2]
                key = f"{filename}::{agent_name}"
                if key not in matches:
                    matches[key] = wins
                else:
                    matches[key] += wins

            # Query for matches involving agent2
            cursor.execute("SELECT agent2_filename, agent2_name, nwins_player2 FROM MATCH")
            rows = cursor.fetchall()
            for row in rows:
                filename = row[0]
                agent_name = row[1]
                wins = row[2]
                key = f"{filename}::{agent_name}"
                if key not in matches:
                    matches[key] = wins
                else:
                    matches[key] += wins

        return matches

    def get_agents(self):
        agents = []
        print('(DB Manager) Looking for agents...')
        if self.conn is not None:
            cursor = self.conn.cursor()
            cursor.execute("SELECT filename, agent_name FROM AGENT")
            rows = cursor.fetchall()
            for row in rows:
                agents.append({'filename': row[0], 'agent_name': row[1]})
        return agents

    def close_connection(self):
        if self.conn is not None:
            self.conn.close()

# Example usage:
if __name__ == "__main__":
    db = DBUtils()
    db.connect()

    # Adding users
    if db.add_user("user1"):
        print("User added successfully.")
    else:
        print("User already exists.")

    # Adding agents
    if db.add_agent("agent1.py", "Agent 1"):
        print("Agent added successfully.")
    else:
        print("Agent already exists.")

    # Adding match result
    if db.add_match_result("agent1.py", "agent2.py", 5, 3):
        print("Match result added successfully.")
    else:
        print("Failed to add match result.")

    db.close_connection()
