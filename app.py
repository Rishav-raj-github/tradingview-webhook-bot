import os
import json
from flask import Flask, request, jsonify
import requests
from binance.spot import Spot
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# ============ BINANCE API CREDENTIALS ============
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')
BINANCE_REAL_API_KEY = os.getenv('BINANCE_REAL_API_KEY')
BINANCE_TESTNET = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'

# ============ FLATTRADE API CREDENTIALS ============
FLATTRADE_API_KEY = os.getenv('FLATTRADE_API_KEY')
FLATTRADE_API_SECRET = os.getenv('FLATTRADE_API_SECRET')
FLATTRADE_USER_ID = os.getenv('FLATTRADE_USER_ID')
FLATTRADE_API_URL = 'https://api.flattrade.in/v2/'

# ============ INITIALIZE BINANCE CLIENT ============
binance_client = None
try:
    if BINANCE_TESTNET:
        binance_client = Spot(
            api_key=BINANCE_API_KEY,
            api_secret=BINANCE_API_SECRET,
            base_url="https://testnet.binance.vision/api"
        )
        print("[INIT] Binance TESTNET client initialized successfully")
    else:
        binance_client = Spot(
            api_key=BINANCE_REAL_API_KEY if BINANCE_REAL_API_KEY else BINANCE_API_KEY,
            api_secret=BINANCE_API_SECRET,
            base_url="https://api.binance.com/api"
        )
        print("[INIT] Binance REAL client initialized successfully")
except Exception as e:
    print(f"[ERROR] Could not initialize Binance client: {e}")
    binance_client = None

# ============ FLATTRADE ORDER HANDLER ============
def place_flattrade_order(symbol, side, quantity, order_type='market'):
    """
    Place order on Flattrade
    """
    try:
        # Prepare headers
        headers = {
            'Authorization': f'Bearer {FLATTRADE_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Prepare payload
        payload = {
            'apikey': FLATTRADE_API_KEY,
            'token': FLATTRADE_USER_ID,
            'symbol': symbol,  # e.g., 'NSE_EQ|INE002A01018' for CIPLA
            'side': side,  # 'BUY' or 'SELL'
            'quantity': int(quantity),
            'price': 0,  # 0 for market order
            'product': 'MIS',  # MIS = intraday, CNC = delivery
            'pricetype': 'MARKET',
            'ordertype': 'REGULAR'
        }
        
        # Send request
        response = requests.post(
            f"{FLATTRADE_API_URL}orders/place",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"[FLATTRADE] Order placed successfully: {result}")
            return {
                'status': 'success',
                'message': f'{side} order executed on Flattrade',
                'orderId': result.get('orderid', 'N/A'),
                'broker': 'FLATTRADE'
            }
        else:
            error_msg = f"Flattrade API error: {response.status_code} - {response.text}"
            print(f"[FLATTRADE ERROR] {error_msg}")
            return {
                'status': 'error',
                'message': error_msg,
                'broker': 'FLATTRADE'
            }
    except Exception as e:
        error_msg = f"Flattrade exception: {str(e)}"
        print(f"[FLATTRADE ERROR] {error_msg}")
        return {
            'status': 'error',
            'message': error_msg,
            'broker': 'FLATTRADE'
        }

# ============ BINANCE ORDER HANDLER ============
def place_binance_order(symbol, side, quantity):
    """
    Place order on Binance (BUY or SELL)
    """
    try:
        if not binance_client:
            return {
                'status': 'error',
                'message': 'Binance client not initialized',
                'broker': 'BINANCE'
            }
        
        if side.upper() == 'BUY':
            # Place BUY order
            order = binance_client.order_market_buy(
                symbol=symbol,
                quantity=float(quantity)
            )
            print(f"[BINANCE] BUY order executed: {order}")
            return {
                'status': 'success',
                'message': f'BUY order executed on Binance',
                'orderId': order.get('orderId'),
                'broker': 'BINANCE'
            }
        
        elif side.upper() == 'SELL':
            # Get account balance first
            account = binance_client.get_account()
            
            # Extract asset from symbol (e.g., 'BTCUSDT' -> 'BTC')
            asset = symbol.replace('USDT', '').replace('BUSD', '').replace('USDC', '')
            
            # Find balance for this asset
            balance = 0
            for asset_balance in account.get('balances', []):
                if asset_balance['asset'] == asset:
                    balance = float(asset_balance.get('free', 0))
                    break
            
            if balance > 0:
                # Place SELL order with available balance
                sell_quantity = min(balance, float(quantity))
                order = binance_client.order_market_sell(
                    symbol=symbol,
                    quantity=sell_quantity
                )
                print(f"[BINANCE] SELL order executed: {order}")
                return {
                    'status': 'success',
                    'message': f'SELL order executed on Binance',
                    'orderId': order.get('orderId'),
                    'broker': 'BINANCE'
                }
            else:
                error_msg = f'Insufficient balance. Available: {balance}, Required: {quantity}'
                print(f"[BINANCE ERROR] {error_msg}")
                return {
                    'status': 'error',
                    'message': error_msg,
                    'broker': 'BINANCE'
                }
        else:
            return {
                'status': 'error',
                'message': f'Invalid side: {side}. Must be BUY or SELL',
                'broker': 'BINANCE'
            }
    
    except Exception as e:
        error_msg = f"Binance exception: {str(e)}"
        print(f"[BINANCE ERROR] {error_msg}")
        return {
            'status': 'error',
            'message': error_msg,
            'broker': 'BINANCE'
        }

# ============ MAIN WEBHOOK ROUTE ============
@app.route('/webhook', methods=['POST'])
def webhook():
    """
    TradingView webhook handler
    Expected JSON payload:
    {
        "symbol": "BINANCE:BTCUSDT" or "NSE_EQ|INE002A01018",
        "side": "BUY" or "SELL",
        "quantity": 0.01,
        "broker": "BINANCE" or "FLATTRADE"
    }
    """
    try:
        # Parse incoming JSON
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data received'
            }), 400
        
        # Extract parameters
        symbol = data.get('symbol', '').strip()
        side = data.get('side', '').strip().upper()
        quantity = data.get('quantity', 0.001)
        broker = data.get('broker', 'BINANCE').strip().upper()
        
        print(f"\n[WEBHOOK] Received: symbol={symbol}, side={side}, quantity={quantity}, broker={broker}")
        
        # Validate inputs
        if not symbol:
            return jsonify({
                'status': 'error',
                'message': 'Symbol is required'
            }), 400
        
        if side not in ['BUY', 'SELL']:
            return jsonify({
                'status': 'error',
                'message': f'Invalid side: {side}. Must be BUY or SELL'
            }), 400
        
        try:
            quantity = float(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except (ValueError, TypeError) as e:
            return jsonify({
                'status': 'error',
                'message': f'Invalid quantity: {quantity}. {str(e)}'
            }), 400
        
        # Route to correct broker
        if broker == 'FLATTRADE':
            result = place_flattrade_order(symbol, side, quantity)
        elif broker == 'BINANCE':
            result = place_binance_order(symbol, side, quantity)
        else:
            return jsonify({
                'status': 'error',
                'message': f'Unknown broker: {broker}. Supported: BINANCE, FLATTRADE'
            }), 400
        
        # Return result
        status_code = 200 if result['status'] == 'success' else 400
        return jsonify(result), status_code
    
    except Exception as e:
        error_msg = f"Webhook exception: {str(e)}"
        print(f"[WEBHOOK ERROR] {error_msg}")
        return jsonify({
            'status': 'error',
            'message': error_msg
        }), 500

# ============ HEALTH CHECK ROUTE ============
@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'binance_client_initialized': binance_client is not None,
        'flattrade_configured': bool(FLATTRADE_API_KEY)
    }), 200

# ============ MAIN ENTRY POINT ============
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"\n[INIT] Flask app starting on port {port}")
    print(f"[INIT] Binance Testnet Mode: {BINANCE_TESTNET}")
    print(f"[INIT] Flattrade API Configured: {bool(FLATTRADE_API_KEY)}")
    app.run(host='0.0.0.0', port=port, debug=False)
