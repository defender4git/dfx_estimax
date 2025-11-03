import MetaTrader5 as mt5
import sys
import json

author = "Nsikak Paulinus"
print("MetaTrader5 package author:", author)
print("MetaTrader5 package version:", mt5.__version__)

if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

account_info = mt5.account_info()
if account_info:
    account_currency = account_info.currency
    print(f"Account currency: {account_currency}")
else:
    print("Failed to retrieve account information")
    mt5.shutdown()
    quit()

# Get terminal info for broker details
terminal_info = mt5.terminal_info()
broker_name = terminal_info.company if terminal_info else "Unknown Broker"
server_name = getattr(terminal_info, 'server', 'Unknown Server') if terminal_info else "Unknown Server"

# Prepare account info for frontend
account_data = {
    "broker": broker_name,
    "server": server_name,
    "login": account_info.login,
    "currency": account_info.currency,
    "balance": account_info.balance,
    "equity": account_info.equity,
    "margin": account_info.margin,
    "margin_free": account_info.margin_free,
    "leverage": account_info.leverage
}

# Output account data as JSON for frontend
print("ACCOUNT_INFO_JSON_START")
print(json.dumps(account_data))
print("ACCOUNT_INFO_JSON_END")

all_symbols = mt5.symbols_get()
symbols = [symbol.name for symbol in all_symbols if symbol.visible]
print("Symbols to check margin:", symbols)

# Initialize results storage
analysis_results = []

def run_profit_analysis(initial_lot, distance, tradesNo, capital, min_capital_ratio, max_capital_ratio):
    # Configuration parameters from inputs
    print(f"Parameters: initial_lot={initial_lot}, distance={distance}, tradesNo={tradesNo}, capital={capital}, min_ratio={min_capital_ratio}, max_ratio={max_capital_ratio}")

    def calculate_profit(order_type, symbol, lot, price, distance, multiplier):
        """Calculate profit for a trade at given distance in points"""
        if order_type == mt5.ORDER_TYPE_BUY:
            target_price = price + (distance / multiplier)
        else:
            target_price = price - (distance / multiplier)

        return mt5.order_calc_profit(order_type, symbol, lot, price, target_price)

    def analyze_position(order_type, symbol, price, capital_params, symbol_params, distance, tradesNo):
        """Analyze position and determine if lot size adjustment is needed"""
        margin = mt5.order_calc_margin(order_type, symbol, capital_params['initial_lot'], price)
        if margin is None or margin <= 0:
            return None

        # Calculate initial values
        profit_per_trade = calculate_profit(order_type, symbol, capital_params['initial_lot'], price, distance, symbol_params['multiplier'])
        total_profit = profit_per_trade * tradesNo if profit_per_trade else None
        margin_ratio = margin / capital_params['capital']

        # Adjustment calculations
        adjustment = {
            'required': False,
            'type': None,
            'target_ratio': None,
            'adjusted_lot': capital_params['initial_lot'],
            'adjusted_margin': margin,
            'adjusted_profit_per_trade': profit_per_trade,
            'adjusted_total_profit': total_profit,
            'message': []
        }

        if margin_ratio > capital_params['max_ratio']:
            adjustment['required'] = True
            adjustment['type'] = 'reduce'
            adjustment['target_ratio'] = capital_params['max_ratio']
        elif margin_ratio < capital_params['min_ratio']:
            adjustment['required'] = True
            adjustment['type'] = 'increase'
            adjustment['target_ratio'] = capital_params['min_ratio']

        if adjustment['required']:
            # Calculate ideal adjusted lot size
            if margin <= 0:
                adjustment['message'].append("Cannot adjust: margin is zero or negative")
                return {
                    'initial': {
                        'lot': capital_params['initial_lot'],
                        'margin': margin,
                        'margin_ratio': margin_ratio,
                        'profit_per_trade': profit_per_trade,
                        'total_profit': total_profit
                    },
                    'adjustment': adjustment
                }

            scale_factor = (capital_params['capital'] * adjustment['target_ratio']) / margin
            ideal_lot = capital_params['initial_lot'] * scale_factor

            # Apply symbol constraints - round to nearest step
            if symbol_params['volume_step'] <= 0:
                adjustment['message'].append("Invalid volume step")
                return {
                    'initial': {
                        'lot': capital_params['initial_lot'],
                        'margin': margin,
                        'margin_ratio': margin_ratio,
                        'profit_per_trade': profit_per_trade,
                        'total_profit': total_profit
                    },
                    'adjustment': adjustment
                }

            adjusted_lot = round(ideal_lot / symbol_params['volume_step']) * symbol_params['volume_step']
            adjusted_lot = max(min(adjusted_lot, symbol_params['volume_max']), symbol_params['volume_min'])

            # Recalculate with adjusted lot
            adj_margin = mt5.order_calc_margin(order_type, symbol, adjusted_lot, price)
            adj_profit = calculate_profit(order_type, symbol, adjusted_lot, price, distance, symbol_params['multiplier'])

            if adj_margin and adj_profit:
                margin_ratio_adj = adj_margin / capital_params['capital']
                # More lenient check - allow slight deviations
                if (margin_ratio_adj >= capital_params['min_ratio'] * 0.95) and (margin_ratio_adj <= capital_params['max_ratio'] * 1.05):
                    adjustment.update({
                        'adjusted_lot': adjusted_lot,
                        'adjusted_margin': adj_margin,
                        'adjusted_profit_per_trade': adj_profit,
                        'adjusted_total_profit': adj_profit * tradesNo
                    })
                    adjustment['message'].append(f"Lot adjusted to {adjusted_lot:.2f} for {margin_ratio_adj*100:.1f}% capital usage")
                else:
                    adjustment['message'].append(f"Unable to find viable adjustment within constraints (would be {margin_ratio_adj*100:.1f}%)")
            else:
                adjustment['message'].append("Margin/profit calculation failed for adjusted lot")

        return {
            'initial': {
                'lot': capital_params['initial_lot'],
                'margin': margin,
                'margin_ratio': margin_ratio,
                'profit_per_trade': profit_per_trade,
                'total_profit': total_profit
            },
            'adjustment': adjustment
        }

    # Main processing loop
    for symbol in symbols:
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info or (not symbol_info.visible and not mt5.symbol_select(symbol, True)):
            print(f"{symbol} - Skipped")
            continue

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"{symbol} - No tick data available")
            continue

        params = {
            'capital': capital,
            'initial_lot': initial_lot,
            'min_ratio': min_capital_ratio,
            'max_ratio': max_capital_ratio
        }

        symbol_params = {
            'volume_min': symbol_info.volume_min,
            'volume_max': symbol_info.volume_max,
            'volume_step': symbol_info.volume_step,
            'digits': symbol_info.digits,
            'multiplier': 10 ** symbol_info.digits
        }

        symbol_result = {
            'symbol': symbol,
            'capital': capital,
            'currency': account_currency,
            'buy': None,
            'sell': None
        }

        # Analyze buy position
        buy_analysis = analyze_position(mt5.ORDER_TYPE_BUY, symbol, tick.ask, params, symbol_params, distance, tradesNo)
        if buy_analysis:
            symbol_result['buy'] = buy_analysis

        # Analyze sell position
        sell_analysis = analyze_position(mt5.ORDER_TYPE_SELL, symbol, tick.bid, params, symbol_params, distance, tradesNo)
        if sell_analysis:
            symbol_result['sell'] = sell_analysis

        if buy_analysis or sell_analysis:
            analysis_results.append(symbol_result)

    # Output results as JSON for frontend
    print("ANALYSIS_RESULTS_JSON_START")
    print(json.dumps({
        'parameters': {
            'initial_lot': initial_lot,
            'distance': distance,
            'trades_no': tradesNo,
            'capital': capital,
            'min_ratio': min_capital_ratio,
            'max_ratio': max_capital_ratio
        },
        'results': analysis_results
    }))
    print("ANALYSIS_RESULTS_JSON_END")

    print("\n" + "="*60)
    print("Analysis complete!")
    mt5.shutdown()

if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) != 7:
        print("Usage: python estimate_profit_v5_web.py <initial_lot> <distance> <tradesNo> <capital> <min_capital_ratio> <max_capital_ratio>")
        sys.exit(1)

    initial_lot = float(sys.argv[1])
    distance = int(sys.argv[2])
    tradesNo = int(sys.argv[3])
    capital = float(sys.argv[4])
    min_capital_ratio = float(sys.argv[5])
    max_capital_ratio = float(sys.argv[6])

    run_profit_analysis(initial_lot, distance, tradesNo, capital, min_capital_ratio, max_capital_ratio)