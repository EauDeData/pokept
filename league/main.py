from sim.simutils import simulate_gen8_random_battle
import asyncio
from flask import Flask, request, jsonify, render_template, g, redirect, url_for
from werkzeug.utils import secure_filename
from db.dbutils import DBUtils
import json
import operator

app = Flask(__name__, template_folder='front')
db = DBUtils(db_name='db/databasev2.db')
app.config['UPLOAD_FOLDER'] = 'sim/agents/'

@app.before_request
def before_request():
    g.db = db
    g.db.connect()
@app.after_request
def after_request(response):
    g.db.close_connection()
    return response

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

        # Create a new SQLite connection for this request
        db.connect()

        # Add agent to the database
        if db.add_agent(filename, agent_name):
            db.close_connection()
            return jsonify({'message': 'Agent uploaded successfully'}), 200
        else:
            db.close_connection()
            return jsonify({'error': 'Agent already exists'}), 400
@app.route('/upload_agent_form')
def upload_agent_form():
    return render_template('upload_agent.html')

@app.route('/run_match_form')
def run_match_form():
    agents = db.get_agents()
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
        {'file_name': agent2_filename.replace('.py', ''), 'agent_name': agent2_name}, nbattles=10)

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
    db.connect()
    db.add_match_result(**data)
    db.close_connection()

    return jsonify(data)
@app.route('/get_matches')
def get_matches():
    matches = db.get_matches()
    # Data:
    # {
    #     "max_power_example.py::MaxDamagePlayer": 19,
    #     "random_agent_example.py::RandomPlayer": 1
    # }
    # Sort matches by number of wins in descending order
    sorted_matches = sorted(matches.items(), key=operator.itemgetter(1), reverse=True)

    # Prepare data for HTML table
    table_data = [{'filename': key.split('::')[0], 'agent': key.split('::')[1], 'nWins': value} for key, value in sorted_matches]

    # Render HTML template with table data
    return render_template('matches.html', table_data=table_data)

if __name__ == "__main__":
    db.connect()
    app.run(host='0.0.0.0', port=5005, debug=True)

