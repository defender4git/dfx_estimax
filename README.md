# DFX Estimax

A web-based profit estimation tool for MetaTrader5 trading accounts.

## Description

This application provides a web interface to analyze potential trading profits across various symbols using MetaTrader5. It calculates margin requirements, profit projections, and suggests lot size adjustments based on capital allocation ratios.

## Features

- Real-time account information display
- Profit analysis for multiple trading symbols
- Lot size optimization based on capital ratios
- Web-based interface for easy access

## Requirements

- Python 3.x
- MetaTrader5 terminal running
- Flask
- MetaTrader5 Python package

## Installation

1. Clone or download the repository.
2. Install required packages:
   ```
   pip install flask MetaTrader5
   ```
3. Ensure MetaTrader5 terminal is running and logged in.

## Usage

1. Run the Flask application:
   ```
   python app.py
   ```
2. Open your browser and navigate to `http://localhost:5000`
3. View account information on the main page.
4. Enter analysis parameters:
   - Initial Lot Size
   - Distance (in points)
   - Number of Trades
   - Capital Amount
   - Minimum Capital Ratio
   - Maximum Capital Ratio
5. Click "Run Analysis" to perform the profit estimation.

## Author

Nsikak Paulinus