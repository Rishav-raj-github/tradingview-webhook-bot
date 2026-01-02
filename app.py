import os
import json
from flask import Flask, request, jsonify
import requests
from binance.spot import Spot
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Binance API credentials
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')
BINANCE_TESTNET = os.getenv('BINANCE_TESTNET', 'True') == 'True'

# Initialize Binance client
if BINANCE_TESTNET:
    client = Spot(BINANCE_API_KEY, BINANCE_API_SECRET, base_url="https://testnet.binance.vision/api")
else:
    client = Spot(BINANCE_API_KEY, BINANCE_API_SECRET)

# Function to close opposite positions
def close_opposite_positions(symbol, action):
    """Close opposite positions when a trade signal is triggered"""
    try:
        # Get account information
        account = client.get_account()
        
        # Determine opposite action
        opposite_action = 'SELL' if action == 'BUY' else 'BUY'
        
        # Extract asset from symbol (e.g., 'BTC' from 'BTCUSDT')
        asset = symbol.replace('USDT', '')
        
        # Get open orders
        open_orders = client.get_open_orders(symbol=symbol)
        
        # Close orders with opposite side
        for order in open_orders:
            if order['side'] == opposite_action:
                try:
                    client.cancel_order(symbol=symbol, orderId=order['orderId'])
                    print(f"Cancelled {opposite_action} order {order['orderId']} for {symbol}")
                except Exception as e:
                    print(f"Could not cancel order {order['orderId']}: {str(e)}")
        
        # Also close open positions if using margin/futures
        # For spot trading, positions are represented by balance
        if opposite_action == 'SELL':
            # Try to sell remaining balance if switching to BUY
            balance = 0
            for asset_balance in account['balances']:
                if asset_balance['asset'] == asset:
                    balance = float(asset_balance['free'])
                    break
            
            if balance > 0:
                try:
                    order = client.order_market_sell(
                        symbol=symbol,
                        quantity=balance
                    )
                    print(f"Closed BUY position: Sold {balance} {asset}")
                    return {'closed': True, 'quantity': balance}
                except Exception as e:
                    print(f"Could not close BUY position: {str(e)}")
        
        return {'closed': False}
    
    except Exception as e:
        print(f"Error closing opposite positions: {str(e)}")
        return {'closed': False, 'error': str(e)}



@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        
        # Extract alert data
        alert_type = data.get('alertType')  # 'BUY' or 'SELL'
        symbol = data.get('symbol', 'BTCUSDT')
        quantity = float(data.get('quantity', 0.001))
        
        if alert_type == 'BUY':
                    # Close opposite positions first
        close_opposite_positions(symbol, 'BUY')
        # Place BUY order
            # Place BUY order
            order = client.order_market_buy(
                symbol=symbol,
                quantity=quantity
            )
            return jsonify({
                'status': 'success',
                'message': f'BUY order executed',
                'orderId': order.get('orderId')
            }), 200
            
        elif alert_type == 'SELL':
                # Close opposite positions first
        close_opposite_positions(symbol, 'SELL')
            # Get account balance first
            account = client.get_account()
            # Find asset balance
            asset = symbol.replace('USDT', '')
            balance = 0
            for asset_balance in account['balances']:
                if asset_balance['asset'] == asset:
                    balance = float(asset_balance['free'])
                    break
            
            if balance > 0:
                # Place SELL order
                order = client.order_market_sell(
                    symbol=symbol,
                    quantity=min(balance, quantity)
                )
                return jsonify({
                    'status': 'success',
                    'message': f'SELL order executed',
                    'orderId': order.get('orderId')
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Insufficient balance for SELL order'
                }), 400
        else:
            return jsonify({
                'status': 'error',
                'message': 'Invalid alert type'
            }), 400
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)
