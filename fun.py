import csv
import os

csv_file = "master_times.csv"

def read_csv(file_path):
    """Read the CSV file and return a list of rows."""
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist.")
        return []
    
    with open(file_path, mode='r', newline='') as file:
        reader = csv.reader(file)
        return [row for row in reader]

def durationToTime(time: str): 
    # Assumes that the duration is formatted properly
    key = [36000, 3600, None, 600, 60, None, 10, 1, None, 0.1, 0.01]  # Value in seconds of each digit of duration
    
    listtime = list(time)
    
    if len(listtime) != len(key):
        raise Exception(f"Attempted to convert duration to time, but failed: '{time}' was not of proper length")
    
    total = 0.0
    for i in range(len(key)):
        if key[i] != None:
            total += int(listtime[i]) * key[i]
    
    return total

data = read_csv(csv_file)
out = []
print(data)

for row in data[1:]:
    if row[6] != '' and row[7] != '':
        out.append((round(durationToTime(row[6]), 2), round(durationToTime(row[7]), 2)))

for i in out:
    print(f"{i[1]}, {i[0]}")