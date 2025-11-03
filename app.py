from flask import Flask, render_template, request
import subprocess
import sys
import os
import json

app = Flask(__name__)

@app.route('/')
def index():
    # Get account info by running the script briefly
    account_info = get_account_info()
    return render_template('index.html', account_info=account_info)

@app.route('/run_analysis', methods=['POST'])
def run_analysis():
    try:
        # Get parameters from form
        initial_lot = request.form.get('initial_lot', '0.5')
        distance = request.form.get('distance', '430')
        trades_no = request.form.get('trades_no', '3')
        capital = request.form.get('capital', '50000')
        min_ratio = request.form.get('min_ratio', '0.2')
        max_ratio = request.form.get('max_ratio', '0.5')

        # Run the estimate_profit_v5_web.py script with parameters
        result = subprocess.run([sys.executable, 'estimate_profit_v5_web.py',
                               initial_lot, distance, trades_no, capital, min_ratio, max_ratio],
                              capture_output=True, text=True, cwd=os.getcwd())
        output = result.stdout
        error = result.stderr

        # Extract account info from output
        account_info = None
        if "ACCOUNT_INFO_JSON_START" in output and "ACCOUNT_INFO_JSON_END" in output:
            start = output.find("ACCOUNT_INFO_JSON_START") + len("ACCOUNT_INFO_JSON_START\n")
            end = output.find("ACCOUNT_INFO_JSON_END")
            json_str = output[start:end].strip()
            try:
                account_info = json.loads(json_str)
            except:
                account_info = None

        # Extract analysis results from output
        analysis_data = None
        if "ANALYSIS_RESULTS_JSON_START" in output and "ANALYSIS_RESULTS_JSON_END" in output:
            start = output.find("ANALYSIS_RESULTS_JSON_START") + len("ANALYSIS_RESULTS_JSON_START\n")
            end = output.find("ANALYSIS_RESULTS_JSON_END")
            json_str = output[start:end].strip()
            try:
                analysis_data = json.loads(json_str)
            except:
                analysis_data = None

        # Remove the JSON markers from output for raw text display if needed
        output = output.replace("ACCOUNT_INFO_JSON_START\n", "").replace("ACCOUNT_INFO_JSON_END\n", "")
        output = output.replace("ANALYSIS_RESULTS_JSON_START\n", "").replace("ANALYSIS_RESULTS_JSON_END\n", "")

        if error:
            output += "\nErrors:\n" + error
    except Exception as e:
        output = f"Error running script: {str(e)}"
        account_info = get_account_info()
        analysis_data = None

    return render_template('index.html', output=output, account_info=account_info, analysis_data=analysis_data)

def get_account_info():
    """Get account info by running a quick script execution"""
    try:
        result = subprocess.run([sys.executable, 'estimate_profit_v5_web.py',
                               '0.01', '1', '1', '1000', '0.1', '0.9'],
                              capture_output=True, text=True, cwd=os.getcwd(), timeout=10)

        output = result.stdout
        if "ACCOUNT_INFO_JSON_START" in output and "ACCOUNT_INFO_JSON_END" in output:
            start = output.find("ACCOUNT_INFO_JSON_START") + len("ACCOUNT_INFO_JSON_START\n")
            end = output.find("ACCOUNT_INFO_JSON_END")
            json_str = output[start:end].strip()
            return json.loads(json_str)
    except:
        pass
    return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)