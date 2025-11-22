from dotenv import load_dotenv
import os
import sqlite3
import time
from datetime import date, timedelta
import numpy as np
import requests
import matplotlib.pyplot as plt

load_dotenv()

# Load env variables
db = os.getenv('db_location')
metadata_id_statistics = os.getenv('metadata_id_statistics')
entity_id = os.getenv('entity_id')
api_token = os.getenv('api_token')
chat_id = os.getenv('chat_id')

# Access db and get weight statistics
conn = sqlite3.connect(db)
cursor = conn.cursor()
cursor.execute("SELECT min, created_ts, max FROM statistics WHERE metadata_id = ?;", (metadata_id_statistics,))
raw_weights = cursor.fetchall()
conn.close()

# Access db to get metadata_id from the states_meta table before getting state data
conn = sqlite3.connect(db)
cursor = conn.cursor()
cursor.execute("SELECT metadata_id FROM states_meta WHERE entity_id = ?;", (entity_id,))
metadata_id_states = cursor.fetchall()
conn.close()

# Access db and get state data for latest weight
conn = sqlite3.connect(db)
cursor = conn.cursor()
cursor.execute("SELECT state, last_updated_ts FROM states WHERE metadata_id = ?;", (metadata_id_states[0][0],))
state_weights = cursor.fetchall()
conn.close()

# Compute first day and current day
firstday = date.fromtimestamp(raw_weights[0][1])
currentday = date.fromtimestamp((time.time()))

# Transform data and fill in gaps first
i = 0 # for iterating the transformed list
j = 0 # for iterating the raw list
totaldays = (currentday - firstday).days + 1
fixed_weights = [[0, None] for _ in range(totaldays)]
totalrows = len(raw_weights)

while True:
    if (firstday + timedelta(days=i)) > currentday:
        break

    # Setting the date
    fixed_weights[i][1] = firstday + timedelta(days=i)

    # Check a value for this date exists
    if date.fromtimestamp(raw_weights[j][1]) == firstday + timedelta(days=i):

        # Check this is the latest entry for that date
        while True:
            if j >= totalrows - 1:
                break
            if date.fromtimestamp(raw_weights[j][1]) == date.fromtimestamp(raw_weights[j + 1][1]):
                j = j + 1
            else:
                break
        
        fixed_weights[i][0] = raw_weights[j][0]
        i = i + 1
        j = j + 1

    # If there isn't a value for this date, use the last one available
    else:
        fixed_weights[i][0] = fixed_weights[i - 1][0]
        i = i + 1

# Update todays weight as the state value as it hasn't entered the statistics SQLite table yet
fixed_weights[len(fixed_weights) - 1][0] = float(state_weights[len(state_weights) - 1][0])

# Calculation of values

# Periods of days to calculate averages
calcs = [92] # 3 months but option to add more here
span = len(fixed_weights)
todaysweight = fixed_weights[span - 1][0]
upordown = []
emoji = []

for days in calcs:
    # Calculate moving average first
    weight_forcalc = []

    for i in range(days):
        weight_forcalc.append(fixed_weights[span - i - 1][0])

    # Calculate trend over the same period
    weight_forcalc_reversed = weight_forcalc[::-1]
    coeff = np.polyfit(range(days), weight_forcalc_reversed , 1)
    if coeff[0] > 0:
        upordown.append("up")
        emoji.append("📈")
    else:
        upordown.append("down")
        emoji.append("📉")

# Calculate exponentially smoothed average

p = 0.1 # Smoothing factor
exsa = [None]*span
exsa[0] = fixed_weights[0][0]

for i in range(1, len(fixed_weights) - 1):
    exsa[i] = exsa[i - 1] + p * (fixed_weights[i][0] - exsa[i - 1])

# Split out data to put into plots
x = [row[1] for row in fixed_weights]
y1 = [row[0] for row in fixed_weights]

# Only get out the last x period of days
daystoplot = calcs[0]
x = x[-daystoplot:]
y1 = y1[-daystoplot:]
exsa = exsa[-daystoplot:]

# Calculate trendline to plot
trendline = np.polyval(coeff, range(days))

# Plot the data
plt.plot(x, y1, linestyle='-', color='black', label='Weight')
plt.plot(x, exsa, linestyle='-', color='blue', label='Exponentially smoothed average')
plt.plot(x, trendline, linestyle='-', color='orange', label='Trendline')
plt.xticks([x[0], x[round(len(x)/2)], x[-1]])

plt.xlabel('Day')
plt.ylabel('Weight (kg)')
plt.legend()
output_file = 'graph.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')

# Send via telegram
message = (
    f'Your weight today is {todaysweight} kg.\n'
    f'3 month trend is going {upordown[0]} {(coeff[0]*365):.2f} kg per year {emoji[0]}'
)

url = f'https://api.telegram.org/bot{api_token}/sendMessage'
url2 = f"https://api.telegram.org/bot{api_token}/sendPhoto"

data = {'chat_id': chat_id, 'text': message}
response = requests.post(url, data=data)

# print(response.json())  # Activate this for debugging

with open(output_file, 'rb') as image:
    response = requests.post(url2, data={'chat_id': chat_id}, files={'photo': image})

# print(response.json())  # Activate this for debugging