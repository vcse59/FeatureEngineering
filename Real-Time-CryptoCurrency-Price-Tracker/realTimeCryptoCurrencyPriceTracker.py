import asyncio
import websockets
import json
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from collections import deque
import matplotlib.dates as mdates
import matplotlib
import random

# Set the backend to TkAgg or another interactive backend
matplotlib.use('TkAgg')

# WebSocket URL for BTC/USDT trades on Binance Testnet
url = "wss://testnet.binance.vision/ws/btcusdt@trade"

# Store last 60 minutes of trades
trades = deque(maxlen=3600)  # Store up to 3600 trade entries (1 per second for 60 mins)

# Function to save trade data to SQLite database
def save_trade_to_db(price, quantity, timestamp):
    trade_time = datetime.fromtimestamp(timestamp / 1000.0)

    # Connect to SQLite database (create if it doesn't exist)
    conn = sqlite3.connect('trades.db')
    cursor = conn.cursor()

    # Create a table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            price REAL,
            quantity REAL,
            timestamp TEXT
        )
    ''')

    # Insert the trade data
    cursor.execute('''
        INSERT INTO trades (price, quantity, timestamp)
        VALUES (?, ?, ?)
    ''', (price, quantity, trade_time))

    # Commit and close the connection
    conn.commit()
    conn.close()

    print(f"Saved trade - Price: {price}, Quantity: {quantity}, Time: {trade_time}")

# Function to plot trades
def plot_trades():
    if len(trades) > 0:
        timestamps, prices, quantities = zip(*trades)

        plt.subplot(2, 1, 1)
        plt.cla()  # Clear the previous plot for real-time updates
        plt.plot(timestamps, prices, label='Price', color='blue')
        plt.ylabel('Price (USDT)')
        plt.legend()
        plt.title('Real-Time BTC/USDT Prices')
        plt.xticks(rotation=45)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

        plt.subplot(2, 1, 2)
        plt.cla()  # Clear the previous plot for real-time updates
        plt.plot(timestamps, quantities, label='Quantity', color='orange')
        plt.ylabel('Quantity')
        plt.xlabel('Time')
        plt.legend()
        plt.xticks(rotation=45)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

        plt.tight_layout()  # Adjust layout for better spacing
        plt.pause(0.1)  # Pause to update the plot

# Asynchronous function to connect to WebSocket and receive trade updates
async def receive_trades():

    reconnect_attempt = 0
    while True:

        async with websockets.connect(url) as ws:
            while True:
                reconnect_attempt = 0
                try:
                    response = await ws.recv()
                    trade_data = json.loads(response)

                    price = float(trade_data['p'])
                    quantity = float(trade_data['q'])
                    timestamp = int(trade_data['T'])

                    trade_time = datetime.fromtimestamp(timestamp / 1000.0)

                    trades.append((trade_time, price, quantity))

                    print(f"Price: {price}, Quantity: {quantity}, Timestamp: {timestamp}")

                    save_trade_to_db(price, quantity, timestamp)

                    plot_trades()  # Update the plot with new trade data

                except websockets.exceptions.ConnectionClosed as e:
                    print(f"WebSocket connection closed: attempting to reconnect")
                    reconnect_attempt += 1
                    wait_time = min(2 ** reconnect_attempt + random.random(), 60)
                    await asyncio.sleep(wait_time) # Exponential backoff
                    break
                except Exception as e:
                    print(f"Error: {e}")

if __name__ == "__main__":
    plt.ion()  # Enable interactive mode for Matplotlib
    plt.figure(figsize=(10, 8))  # Set figure size
    asyncio.get_event_loop().run_until_complete(receive_trades())
