from sim.simutils import simulate_gen8_random_battle
from flask import Flask, request, jsonify, render_template, g, redirect, url_for
from werkzeug.utils import secure_filename
from db.dbutils import DBUtils
import json
import seaborn as sns
import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg before importing matplotlib.pyplot
import matplotlib.pyplot as plt
import base64
import io
import sqlite3
import numpy as np

db_name = 'db/databasev2.db'
app = Flask(__name__, template_folder='front')
app.config['UPLOAD_FOLDER'] = 'sim/agents/'
app.config['DATABASE'] = db_name

# Before init #
db = sqlite3.connect(app.config['DATABASE'])
DBUtils.create_tables(db.cursor(), db)
db.close()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/upload_agent', methods=['POST'])
def upload_agent():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    agent_name = request.form.get('agent_name')
    if agent_name is None:
        return jsonify({'error': 'Agent name is required'}), 400

    if file:
        filename = secure_filename(file.filename)
        file_path = app.config['UPLOAD_FOLDER'] + filename
        file.save(file_path)
        if not f"class {agent_name}" in '\n'.join(open(file_path, 'r').readlines()):
            return jsonify({'error': f'class {agent_name} is not in file.'}), 400

        # Create a new SQLite connection for this request
        database = get_db()

        # Add agent to the database
        if DBUtils.add_agent(database.cursor(), database, filename, agent_name):
            return jsonify({'message': 'Agent uploaded successfully'}), 200
        else:
            return jsonify({'error': 'Agent already exists'}), 400
@app.route('/upload_agent_form')
def upload_agent_form():
    return render_template('upload_agent.html')

@app.route('/run_match_form')
def run_match_form():
    database = get_db()
    agents = DBUtils.get_agents(database.cursor())
    print(agents)
    return render_template('run_match.html', agents=agents)


@app.route('/run_match', methods=['POST'])
async def run_match():
    agent1_value = request.form.get('agent1_filename')
    agent2_value = request.form.get('agent2_filename')
    # Split the value to extract filename and agent name
    agent1_filename, agent1_name = agent1_value.split(' - ', 1)
    agent2_filename, agent2_name = agent2_value.split(' - ', 1)

    # Now you have both filename and agent name
    print(f"Selected agents: {agent1_filename} - {agent1_name}, {agent2_filename} - {agent2_name}")

    player1_wins, player2_wins = await simulate_gen8_random_battle(
        {'file_name': agent1_filename.replace('.py', ''), 'agent_name': agent1_name},
        {'file_name': agent2_filename.replace('.py', ''), 'agent_name': agent2_name}, nbattles=50)

    data = {'nwins_player1': player1_wins,
                    'nwins_player2': player2_wins,
                    'agent1_filename': agent1_filename,
                    'agent1_name': agent1_name,
                    'agent2_filename': agent2_filename, 'agent2_name': agent2_name}
    return redirect(url_for('upload_matches', data=json.dumps(data)))

@app.route('/upload_matches')
def upload_matches():
    # Retrieve data from URL parameters or session
    data = json.loads(request.args.get('data')) # or request.session.get('data')
    print('Your data is', data, 'of type', type(data))

    database = get_db()
    DBUtils.add_match_result(database.cursor(), database, **data)

    return jsonify(data)
@app.route('/get_matches')
def get_matches():
    database = get_db()
    matches = DBUtils.get_matches(database.cursor())
    # Matches:
    # {'PacifistDamagePlayer::vegan_pokemon_strategy.py': {'MaxDamagePlayer::max_power_example.py': 1},
    # 'MaxDamagePlayer::max_power_example.py': {'PacifistDamagePlayer::vegan_pokemon_strategy.py': 9}}
    # Create a list of unique agents
    agents = list(x for x in matches)
    win_matrix = []
    for agent_1 in agents:
        win_matrix.append(list())
        for agent_2 in agents:

            a1_2 = matches.get(agent_1, {}).get(agent_2, 0)
            a2_1 = matches.get(agent_2, {}).get(agent_1, 0)
            if not (a2_1 + a1_2):
               res = 0
            else:
               res = a1_2 / (a2_1 + a1_2)
            win_matrix[-1].append(round(res, 2))
    with app.app_context():
        # Create the heatmap
        fig, ax = plt.subplots(figsize=(5, 4))
        agents = [ag.split('::')[0] for ag in agents]
        masked_win_matrix = np.eye(len(win_matrix), dtype=bool)
        sns.heatmap(win_matrix, annot=True, cmap='coolwarm', xticklabels=agents, mask=masked_win_matrix,
                    yticklabels=agents, ax=ax)
        ax.set_title('Agent Wins Heatmap')

        # Rotate the tick labels
        plt.xticks(rotation=45)
        plt.yticks(rotation=45)
        ax.set_xlabel('Lose Rate')
        ax.set_ylabel('Win Rate')

        # Adjust layout to make room for tick labels
        plt.tight_layout()
        # Save the heatmap image to a BytesIO object
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png')
        buffer.seek(0)

        # Encode the image as base64
        encoded_image = base64.b64encode(buffer.getvalue()).decode()

        # Close the plot and clear the figure to free resources
        plt.close(fig)

    return f'<img src="data:image/png;base64,{encoded_image}">'

@app.route('/index')
@app.route('/index.html')
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5005, debug=True)

