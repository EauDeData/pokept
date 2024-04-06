# People should be able to upload files with strategies
# Once a strategy is uploaded, main.py will trigger a simutils function to run the simulations
# In front it will be shown (thanks to flask) the current state of the league
import sqlite3
import uuid

class DBUtils:

    @staticmethod
    def create_tables(cursor, conn):
        cursor.execute('''CREATE TABLE IF NOT EXISTS USERS (
                            username TEXT PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS AGENT (
                            filename TEXT PRIMARY KEY,
                            agent_name TEXT
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS MATCH (
                            id TEXT PRIMARY KEY,
                            agent1_filename TEXT,
                            agent1_name TEXT,
                            agent2_filename TEXT,
                            agent2_name TEXT,
                            nwins_player1 INTEGER,
                            nwins_player2 INTEGER,
                            FOREIGN KEY (agent1_filename, agent1_name) REFERENCES AGENT(filename, agent_name),
                            FOREIGN KEY (agent2_filename, agent2_name) REFERENCES AGENT(filename, agent_name)
                        )''')
        conn.commit()

    @staticmethod
    def add_agent(cursor, conn, filename, agent_name):
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO AGENT (filename, agent_name) VALUES (?, ?)", (filename, agent_name))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    @staticmethod
    def add_match_result(cursor, conn, agent1_filename, agent1_name, agent2_filename, agent2_name, nwins_player1, nwins_player2):
        try:
            match_id = str(uuid.uuid4())  # Generate a random UUID
            cursor.execute("INSERT INTO MATCH "
                           "(id, agent1_filename, agent1_name, agent2_filename, agent2_name, nwins_player1, nwins_player2) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (match_id, agent1_filename, agent1_name, agent2_filename, agent2_name, nwins_player1, nwins_player2))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    @staticmethod
    def get_matches(cursor):
        matches = dict()
        # Query all matches from the database
        cursor.execute("SELECT agent1_filename, agent1_name, agent2_filename, agent2_name, nwins_player1, nwins_player2 FROM MATCH")
        rows = cursor.fetchall()
        for row in rows:
            agent1_key = f"{row[1]}::{row[0]}"  # Construct key for agent 1
            agent2_key = f"{row[3]}::{row[2]}"  # Construct key for agent 2

            if not agent1_key in matches: matches[agent1_key] = {}
            if not agent2_key in matches: matches[agent2_key] = {}

            nwins_player1 = row[4]  # Number of wins for agent 1
            nwins_player2 = row[5]  # Number of wins for agent 2

            # If the match exists in the dictionary, update the wins
            if agent2_key in matches[agent1_key]:
                matches[agent1_key][agent2_key] += nwins_player1
                matches[agent2_key][agent1_key] += nwins_player2
            else:
                matches[agent1_key][agent2_key] = nwins_player1
                matches[agent2_key][agent1_key] = nwins_player2

        return matches

    @staticmethod
    def get_agents(cursor):
        print('(DB Manager) Looking for agents...')
        agents = []
        cursor.execute("SELECT filename, agent_name FROM AGENT")
        rows = cursor.fetchall()
        for row in rows:
            agents.append({'filename': row[0], 'agent_name': row[1]})
        return agents


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
