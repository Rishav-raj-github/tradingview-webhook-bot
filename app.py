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
    client = Spot(BINANCE_API_KEY, BINANCE_API_SECRET, base_url="https://testnet.binance.vision/api")else:
    client = Spot(BINANCE_API_KEY, BINANCE_API_SECRET)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        
        # Extract alert data
        alert_type = data.get('alertType')  # 'BUY' or 'SELL'
        symbol = data.get('symbol', 'BTCUSDT')
        quantity = float(data.get('quantity', 0.001))
        
        if alert_type == 'BUY':
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
