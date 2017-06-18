from flask import Flask, request, jsonify
from preprocessing_for_git import get_cluster_for_profession

app = Flask(__name__)


@app.before_first_request
def load_model():
	dicti = {}
	with open("final_clusters.csv") as infile:
		for line in infile:
			dicti[line.split(',')[0]] = line.split(',')[3].replace("\n", "")
	app.database = dicti


@app.route('/', methods=['GET'])
def index():
	return app.send_static_file('index.html')

@app.route('/api/check', methods=['POST'])
def api_check():
	text = request.form['text']
	return jsonify({
		"cluster": get_cluster_for_profession(text, app.database)
	})

if __name__ == '__main__':
    app.run(debug=True)