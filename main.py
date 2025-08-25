print("Importing libraries...")

import csv
import re
import os
import requests
from typing import Any

from relay_tools import *

print("Libraries imported successfully.")

def downloadSwimResultsHTML(sex, strokenum, distance):
    s = requests.Session()
    resp1 = s.get("https://sports-tek.active.com/tmonline/")
    try:
        resp1.raise_for_status()
    except requests.HTTPError:
        return
    payload = {
    'STRIPPED': 'BCSSAProvincialOffice',
    'SETTEAM': 'T'
    }
    
    resp2 = s.get("https://sports-tek.active.com/tmonline/index.asp?STRIPPED=BCSSAProvincialOffice", data=payload)
    try:
        resp2.raise_for_status()
    except requests.HTTPError:
        return
    
    url = rf"https://sports-tek.active.com/tmonline/aTeamResults.asp?Sex={sex}&Stroke={strokenum}&Distance={distance}&Course=S&Fastest=1&TEAM=0&CODE=BCSSA%20Provincial%20Office&Low=&High=&thePage=1&PageSize=100000&STD=false&DB=upload\BCSSAProvincialOffice.mdb&Division=&Region="
    resp3 = s.get(url)
    
    try:
        resp3.raise_for_status()
    except requests.HTTPError:
        return
    
    strokeToShorthand = {"1": "FR", "2": "BK", "3": "BR", "4": "FL", "5": "IM"}
    output_path = f"{sex}_{distance}_{strokeToShorthand[strokenum]}.html"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(resp3.text)
    
    return


def createEventParameters():
    sexes = ["M", "F"]
    strokes = ["1", "2", "3", "4", "5"]
    distances = ["50", "100", "200"]
    
    combos = []
    
    for sex in sexes:
        for stroke in strokes:
            for distance in distances:
                if stroke == "5" and distance == "50": continue  # No 50IM
                if stroke != "5" and distance == "200": continue  # No 200 strokes except IM
                combos.append([sex, stroke, distance])
    
    return combos

def ensureNeededFiles():
    """Ensures that the needed files for operations exist."""
    if not os.path.exists(html_folder_name):
        os.makedirs(html_folder_name)
        print(f"Created folder: {html_folder_name}")
    else:
        print(f"Folder already exists: {html_folder_name}")
    
    if not os.path.exists(csv_output_file_name):
        with open(csv_output_file_name, 'w', newline='') as f:
            pass
        print(f"Created file: {csv_output_file_name}")
    
    if not os.path.exists(swimmer_info_file_name):
        with open(swimmer_info_file_name, 'w', newline='') as f:
            pass
        print(f"Created file: {swimmer_info_file_name}")

def parseHTMLFile(filename: str):
    with open(filename, 'r', encoding='utf-8') as f:
        html = f.read()
    
    html = html.encode('latin1').decode('utf-8')  # Fix Unicode glyph misbehaving
    html.split('<tr class="trow">')[1:]  # Split along data rows and ignore first portion (headers + JS)
    datalines = [i.replace("\n", "").replace("\t", "").strip() for i in html]
    
    pattern = re.compile(r"""
        ^.*?>([a-zA-ZÀ-ž\-' ()\.]+?),\s*([a-zA-ZÀ-ž\-' ()\.]+?)<.*?td align=center width="\d{2}">\s*?(Div\d|Cat\d|)\s*?<.*?>(\d{2}\.\d{2}|\d{0,2}:\d{2}\.\d{2}).*?>([A-Z]{1,}[A-Z!\d ]*).*?&nbsp.*$
    """)
    
    results = []
    for line in datalines:
        result = pattern.search(line)
        if result:
            results.append(list(result.groups()))
            
    
    for r in results:
        r[2] = r[2] or "Div1"
    
    results = [r[1] + " " + r[0], r[2], r[3], r[4] for r in results]
    
    eventName = "".join("".join(filename.split("_")[1:]).split(".")[0]).upper()
    return eventName, results


def readCSV(csvName: str):
    rows = []
    with open(csvName, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            rows.append(row)
    
    return rows

def writeCSV(csvName: str, rows: list[Any]):
    with open(csvName, 'w', newline='') as csvfile:
        csv.writer(csvfile).writerows(rows)

def getSwimmerList(filename, from_timelist=False):
    if from_timelist:
        return [[entry[0], entry[1]] for entry in readCSV(filename) if entry[0] and entry[1]][1:]
    
    return readCSV(filename)[1:]

def sanitize_entries(times, swimmerlist):
    out = []
    onlyNames = [i[0] for i in swimmerlist]
    
    for entry in times:
        if entry[0] in onlyNames:
            out.append(entry)
    
    return out

def fixDurationFormatting(time: str):
    t = list(time)  # Split into characters
    t = [num for num in t if num.isnumeric()]  # Leave only numbers
    
    out = ['', '', '.', '', '', ':', '', '', ':', '', '']  # Duration, starting backwards
    
    for i in range(len(out)):  # Iterate over digits of output
        if len(t) == 0:
            for j in range(i, len(out)):
                if out[j] == '':
                    out[j] = '0'
            break
        if out[i] == '':
            out[i] = t.pop()
        
    out.reverse()
    return "".join(out)

def timeToDuration(time: float) -> str:
    if not isinstance(time, (float, int)):
        raise TypeError("time must be a float or int")
    if time < 0:
        raise Exception(f"Attempted to convert invalid time to duration: {time}")
    if time == 0:
        return "00:00:00.00"
    
    hours = int(time // 3600)
    time %= 3600
    minutes = int(time // 60)
    seconds = int(time % 60)
    dd = round(round(time - int(time), 2)*100)
    
    return f"{hours:02}:{minutes:02}:{seconds:02}.{dd:02}"

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

def cleanUpCSV(swimmerInfo: list[list[str]], csvData : list[list[str]]):
    
    # Ensure first row actually works
    if len(csvData) != 0:
        csvData[0] = ['Name','Div.','100IM','200IM','50FL','100FL','50BK','100BK','50BR','100BR','50FR','100FR']
    else:
        csvData = [['Name','Div.','100IM','200IM','50FL','100FL','50BK','100BK','50BR','100BR','50FR','100FR']]
    
    lengthOfRow = len(csvData[0])
    csvNames = [i[0] for i in csvData[1:]]
    
    # Check for updated or deleted swimmers
    for i in range(len(csvData)-1, 0, -1):  # Start from the end to avoid index issues with popping
        swimmer_entry = [csvData[i][0], csvData[i][1]]
        swimmer_string = f"{swimmer_entry[0]} ({swimmer_entry[1]})"
        if swimmer_entry not in swimmerInfo:
            choice = input(f"Swimmer {swimmer_string} not found in swimmer list. Remove from CSV? (y/n): ").lower().strip()
            if choice in {"y", "yes"}:
                csvData.pop(i)
                print(f"Swimmer {swimmer_string} removed from CSV.")
            elif choice in {"n", "no"}:
                print(f"Keeping swimmer {swimmer_string}.")
            else:
                print(f"Invalid input, keeping swimmer {swimmer_string}.")
    
    # Ensure all swimmers are added to CSV
    for swimmer in swimmerInfo:
        if swimmer[0] in csvNames:
            continue
        
        else:
            csvData.append([swimmer[0], swimmer[1]] + [''] * (lengthOfRow-2))
            print(f"Swimmer {swimmer[0]} ({swimmer[1]}) was not found in sheet, and was added to the CSV.")
    
    csvData[1:] = sorted(csvData[1:], key=lambda x: x[0])  # Sort CSV by first name, excluding header row
    
    for row in csvData:
        if row[0] == "Name": continue  # Skip header row
        for i in range(2, len(row)):  # Starts at 2 because of name and DivG
            if row[i] == '' or row[i] == '00:00:00.00':  # Don't do anything to empty cells
                row[i] = ''  # Remove zero-times
                continue
            row[i] = fixDurationFormatting(row[i])  # Ensure duration formatting
    
    return csvData

def writeEventToCSV(eventName : str, csvData : list[list[str]], times : list[list[str]], force_write: bool = False):
    global ignoreOtherMissingNamesFlag, new_times, updated_times
    
    # Find event index
    eventIndex = -1
    for i in range(len(csvData[0])):
        if csvData[0][i] == eventName:
            eventIndex = i
            break
    else:
        raise Exception(f"Unable to find event name '{eventName}' in CSV header.")
    
    # Write times to rows
    for time in times:
        for row in csvData:
            if time[0] == row[0]:  # Found right name
                formattedTime = fixDurationFormatting(time[1])
                
                # Check a better time than current or if time is empty
                if row[eventIndex] == '':
                    # print(f"Writing {formattedTime} to EMPTY cell of swimmer: {time[0]}, index {eventIndex} ({eventName})")
                    row[eventIndex] = formattedTime
                    new_times += 1
                
                elif durationToTime(formattedTime) < durationToTime(row[eventIndex]) or (
                    force_write and durationToTime(formattedTime) >= durationToTime(row[eventIndex])):
                    # Redundant for casting tomfooleries
                    
                    # print(f"Overwriting with {formattedTime} to {row[eventIndex]} swimmer: {time[0]}, index {eventIndex} ({eventName})")
                    row[eventIndex] = formattedTime
                    updated_times += 1
                # else:
                    # print(f"Equal or better time found: {formattedTime} to {row[eventIndex]} swimmer: {time[0]}, index {eventIndex} ({eventName})")
                break
        
        else: 
            if ignoreOtherMissingNamesFlag == False or ignoreOtherMissingNamesFlag is None:
                print(csvData)
                c = input(f"Unable to find '{time[0]}' in CSV. Continue with operation? (y/n) ").lower().strip()
                
                if c in {"n", "no"}:
                    raise Exception(f"Execution stopped due to missing name: {time[0]}")
                
                elif c in {"y", "yes"} and ignoreOtherMissingNamesFlag is None:
                    c = input(f"Hide prompt warning for future missing names? (y/n) ").lower().strip()
                    
                    if c in {"y", "yes"}:
                        ignoreOtherMissingNamesFlag = True
                        print("Will NOT prompt for any further invalid names.")
                    
                    else:
                        ignoreOtherMissingNamesFlag = False
                        print("Will continue to prompt for further invalid names.")
            
            print(f"ERROR IGNORED. Continuing operation. Entry ignored: \n\t{time}\t{eventName}")
    
    return csvData

def getPDFData(pdf_folder_name: str):
    print(f"Grabbing files from folder: {pdf_folder_name}")
    
    files = os.listdir(pdf_folder_name)
    data = []
    
    if len(files) == 0:
        print("WARNING: No files found in PDF folder.")
        return data
    else:
        print(f"Found {len(files)} files in PDF folder.")
    
    for file in files:
        if file[-4:] != ".pdf":
            print(f"Warning: Non-PDF file found in PDF folder: {file}")
            continue
        data.append(parseHTMLFile(f"{pdf_folder_name}/{file}"))
        print(f"Extracted times from {pdf_folder_name}/{file}")
    
    return data

def downloadPDFs():
    ensureNeededFiles()  # Ensure the folder exists
    print("Creating event parameters...")
    events = createEventParameters()
    print("Beginning event data fetch...")
    getAllEvents(events)
    print("Event data download complete.")

def outputDataToCSV():
    ensureNeededFiles()
    print("Decoding PDF Data...")
    timeData = getPDFData(html_folder_name)  # Decode PDF data
    
    print("Retrieving master swimmer list...")
    sList = getSwimmerList(swimmer_info_file_name)  # Retrieve swimmer list
    
    print("Sanitizing times from swimmer list...")
    timeData = [(event, sanitize_entries(race, sList)) for (event, race) in timeData]  # Sanitize times
    
    print("Reading CSV data...")
    timeCSV = readCSV(csv_output_file_name)
    
    print("Cleaning time-list data...")
    timeCSV = cleanUpCSV(sList, timeCSV)
    
    print("Adding times to time-list...")
    for chunk in timeData:
        timeCSV = writeEventToCSV(chunk[0], timeCSV, chunk[1])
        print(f"Finished writing {chunk[0]}.")
    
    print("Writing time-list to CSV...")
    with open(csv_output_file_name, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerows(timeCSV)
    print("Write complete.")

def manualEntryPrompt():
    print("\nEntering Manual Entry Mode.\n")
    print("Type 'q' at any prompt to quit, or 'r' to restart your current entry.")
    print("Prefix name or event with '*' to persist across entries.")
    print("Example: '*John Doe' will persist name, which can be auto-entered if an input is left blank.")

    persistent_name = None
    persistent_event = None

    while True:
        name = input("\nMANUAL ENTRY - Enter swimmer's name: ").strip()
        
        if name.lower() == 'q':
            break
        
        if name.lower() == 'r':
            print("Restarting current entry.")
            continue
        
        if name.startswith("*"):
            persistent_name = name[1:].strip()
            name = persistent_name
        
        elif name == "":
            if persistent_name:
                name = persistent_name
                print(f"Using persistent name: {name}")
            else:
                print("No name provided and no persistent name set.")
                continue

        swimmer_info = getSwimmerList(csv_output_file_name, from_timelist=True)  # Load swimmer list
        
        # Use fuzzy search for matching names
        matches = name_fuzzy_search(name, swimmer_info)
        new_swimmer = False
        if len(matches) == 0:
            print(f"No swimmer found matching: {name}")
            division = input("Enter division (e.g., 3B): ").strip().upper()
            new_swimmer = True
        
        elif len(matches) == 1:
            name = matches[0][0]
            division = matches[0][1]
            print(f"Swimmer found: {name} with division {division}")
        
        else:
            print("Multiple swimmers found:")
            for idx, match in enumerate(matches, 1):
                print(f"{idx}: {match[0]} ({match[1]})")
            try:
                choice = int(input("Select swimmer by number: ").strip())
                selected = matches[choice - 1]
                name = selected[0]
                division = selected[1]
                print(f"Selected {name} ({division}).")
            except Exception as e:
                print("Invalid selection. Please try again.")
                continue
        
        if division.lower() == 'q':
            break
        if division.lower() == 'r':
            print("Restarting current entry.")
            continue
        elif division == "":
            print("No division provided, restarting entry.")
            continue
        
        # Validate division
        if new_swimmer:
            valids = [f"{n}B" for n in range(1, 9)] + [f"{n}G" for n in range(1, 9)] + ["O1G", "O2G", "O1B", "O2B"]
            if division not in valids:
                print("Division not found in valids.")
                continue
        
        timeCSV = cleanUpCSV(swimmer_info + [[name, division]], readCSV(csv_output_file_name))

        event = input(
                f"Enter event{' or time (E: '+persistent_event+')' 
                if persistent_event is not None else ''}: "
            ).strip().upper().replace(' ', '')
        
        if not any(i.isalpha() for i in list(event)) and persistent_event is not None:
            # Assume times are input into the event if a persistent event is defined
            # and there are no letters in the event.
            raw_time = event
            event = persistent_event
            
        else:
            if event.lower() == 'q':
                break
            
            if event.lower() == 'r':
                print("Restarting current entry.")
                continue
            
            if event.startswith("*"):
                persistent_event = event[1:].strip()
                event = persistent_event
            
            elif event == "":
                if persistent_event:
                    event = persistent_event
                    print(f"Using persistent event: {event}")
                
                else:
                    print("No event provided and no persistent event set. Restarting entry.")
                    continue
            
            try:
                event_index = timeCSV[0].index(event)
            except ValueError:
                print("Event not found.")
                continue
            
            raw_time = input("Enter time (e.g., 14256 or 1:42.56): ").strip()
        
        if raw_time.lower() == 'q':
            break
        
        if raw_time.lower() == 'r':
            print("Restarting current entry.")
            continue

        try:
            formatted_time = fixDurationFormatting(raw_time)

            # Find or add swimmer row
            row_found = False
            for row in timeCSV:
                if row[0] == name:
                    row_found = True
                    existing_time = row[event_index]
                    break

            if not row_found:
                raise Exception(f"Swimmer {name} not found in timeCSV after cleanUpCSV. (Should be impossible)")

            # Add swimmer to list for time pulling if new name
            if new_swimmer:
                name_list = readCSV(swimmer_info_file_name)
                name_list.append([name, division])
                writeCSV(swimmer_info_file_name, name_list)
            
            # Overwrite warning if applicable
            should_write = True
            if existing_time:
                new_secs = durationToTime(formatted_time)
                existing_secs = durationToTime(existing_time)
                if new_secs > existing_secs:
                    print(f"⚠️ Warning: {name}'s existing time for {event} is faster ({existing_time}) than new time ({formatted_time}).")
                    confirm = input("Do you want to overwrite it? (y/n): ").strip().lower()
                    if confirm not in {"y", "yes"}:
                        should_write = False
                        print("Entry skipped.")
                        continue

            if should_write:
                timeCSV = writeEventToCSV(event, timeCSV, [[name, formatted_time]], force_write=True)
                with open(csv_output_file_name, 'w', newline='') as csvfile:
                    csv.writer(csvfile).writerows(timeCSV)
                print(f"✅ Time {formatted_time} recorded for {name} in {event}.\n")

        except Exception as e:
            print(f"❌ Error: {e}\n")

modeprompt = """
What operation do you want to perform?
\t1. Full run (download + write)
\t2. Download PDFs
\t3. Decode PDFs and write to CSV output
\t4. Manual time entry
\t5. Relay tool
\tQ. Exit
"""

html_folder_name = "grabbed_htmls"
swimmer_info_file_name = "swim_info.csv"
csv_output_file_name = "master_times.csv"

new_times = 0
updated_times = 0
ignoreOtherMissingNamesFlag = None

def main():
    global new_times, updated_times
    while True:
        mode = input(modeprompt).strip()
        try:
            if mode.lower() == 'q':
                print("Exiting program.")
                return
            mode = abs(int(mode))
        except Exception as e:
            print(f"Did not recognize input as number. Error: {e}")
            return
        
        new_times = 0
        updated_times = 0
        match mode:
            case 1:
                downloadPDFs()
                outputDataToCSV()
                print(f"New times added: {new_times}")
                print(f"Updated times: {updated_times}")
            case 2:
                downloadPDFs()
            case 3:
                outputDataToCSV()
                print(f"New times added: {new_times}")
                print(f"Updated times: {updated_times}")
            case 4:
                manualEntryPrompt()
            case 5:
                if not(medley_main()):
                    input("Press Enter to continue...")
            case _:
                print("Unexpected error, exiting program.")
                return

if __name__ == "__main__":
    main()