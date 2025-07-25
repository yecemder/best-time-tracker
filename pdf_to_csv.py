import csv
from pypdf import PdfReader
import re
import os
import requests
from weasyprint import HTML, CSS

from make_medley_relay import *

css = CSS(string="""
@page {
    size: 8.5in 1000in;
    margin: 0.01in;
}

@media print {
    body {
        font-family: sans-serif;
        color: black;
        background: white;
    }

    .no-print {
        display: none;
    }
}
""")

def downloadSwimResultsPdf(url, output_path):
    resp = requests.get(url)
    resp.raise_for_status()
    HTML(string=resp.text, base_url=url).write_pdf(output_path, stylesheets=[css])

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

def getAllEvents(combos):
    strokeToShorthand = {"1": "FR", "2": "BK", "3": "BR", "4": "FL", "5": "IM"}
    urls = []
    for c in combos:
        urls.append((fr"https://sports-tek.active.com/tmonline/aTeamResults.asp?Sex={c[0]}&Stroke={c[1]}&Distance={c[2]}&Course=S&Fastest=1&TEAM=35&CODE=Burnaby%20Mountain%20Mantas&Low=&High=&thePage=1&PageSize=999&STD=false&DB=upload\BCSSAProvincialOffice.mdb&Division=&Region=", c))
    
    for link, event in urls:
        downloadSwimResultsPdf(
            link,
            f"grabbed_pdfs/{event[0]}{event[2]}{strokeToShorthand[event[1]]}.pdf"
        )
        print(f"Finished {event[0]}{event[2]}{strokeToShorthand[event[1]]}")
    return

def readPDFFile(filename: str):
    """Parses a PDF file with best times and returns list of lines with best times.

    Args:
        filename (str): The PDF to parse.

    Returns:
        list: A list of strings each containing each line of the times extracted.
    """
    reader = PdfReader(filename)

    parts = ""
    for page in reader.pages:
        parts += page.extract_text()
    
    text_body = "".join(parts).split("\n")
    output = []
    for line in text_body:
        if len(line) > 0 and line[0].isnumeric():
            output.append(line)
        if line[:4] == "Fema" or line[:4] == "Male":
            output.insert(0, line)
    
    return [i.strip() for i in output]

def readCSV(csvName: str):
    rows = []
    with open(csvName, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            rows.append(row)
    
    return rows

def extractTimes(lines: list[str]) -> tuple[str, list[list[str]]]:
    output = []
    nameTimePattern = re.compile(
        r"^\s*\d+\s*([a-zA-Z\-' ()]+?),\s*([a-zA-Z\-' ()]+?)(?=\s?\d+)\s*\w+\s*(\d{0,2}:?\d{2}\.\d{2}).*$"
    )
    for line in lines[1:]:
        result = nameTimePattern.search(line)
        if result:
            output.append(list(result.groups()))
    
    output = [[res[1] + " " + res[0], res[2]] for res in output]
    
    firstline = lines[0].strip()
    
    if "Female" in firstline:
        firstline = firstline[7:-6]
    elif "Male" in firstline:
        firstline = firstline[5:-6]
    else:
        raise Exception(f"Can't determine gender classification from first line '{firstline}'")
    
    event = ""
    i = len(firstline)-1
    while i >= 0:
        if firstline[i].isnumeric() or firstline[i] == " ":
            break
        event = firstline[i] + event
        i -= 1
    
    distance = firstline[0:i].strip()
    
    eventToShorthand = {
        "Free": "FR",
        "Back": "BK",
        "Fly": "FL",
        "Breast": "BR",
        "IM": "IM"
    }
    
    shorthand = eventToShorthand.get(event)
    
    if shorthand:
        print(f"Successfully deciphered event: {firstline} -> {distance+shorthand}")
        return distance + shorthand, output
    else:
        raise Exception(f"Unable to decipher event: {firstline}")

def getSwimmerList(filename, from_timelist=False):
    if from_timelist:
        data = readCSV(filename)
        return [[entry[0], entry[1]] for entry in data if entry[0] and entry[1]][1:]
    output = readCSV(filename)
    return output[1:]

def sanitize_entries(times, swimmerlist):
    out = []
    onlyNames = [i[0] for i in swimmerlist]
    for entry in times:
        if entry[0] in onlyNames:
            out.append(entry)
    return out

def fixDurationFormatting(time: str):
    t = list(time)
    t.reverse()
    out = ['', '', ':', '', '', ':', '', '', '.', '', '']
    out.reverse()
    
    for i in range(len(out)):
        if i>=len(t):
            for j in range(i, len(out)):
                if out[j] == '':
                    out[j] = '0'
            break
        out[i] = t[i]
    return "".join(list(reversed(out)))

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
            print(f"Swimmer {swimmer[0]} was not found in sheet, has added to the CSV.")
    
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
    for file in files:
        if file[-4:] != ".pdf":
            print(f"Warning: Non-PDF file found in PDF folder: {file}")
            continue
        data.append(extractTimes(readPDFFile(f"{pdf_folder_name}/{file}")))
        print(f"Extracted times from {pdf_folder_name}/{file}")
    
    return data

def downloadPDFs():
    events = createEventParameters()
    print("Beginning event data fetch...")
    getAllEvents(events)
    print("Event data download complete.")

def outputDataToCSV():
    print("Decoding PDF Data...")
    timeData = getPDFData(pdf_folder_name)  # Decode PDF data
    
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

def smartTimeFormat(user_input: str) -> str:
    """Convert loose formats like '14256' or '3934' into standard time durations.
    (e.g., '14256' -> '00:01:42.56', '3934' -> '00:00:39.34')"""
    user_input = user_input.strip()
    if ':' in user_input:
        return fixDurationFormatting(user_input)
    
    # Accept formats like 14256 -> 1:42.56
    digits = re.sub(r'\D', '', user_input)
    if not digits.isdigit():
        raise ValueError("Invalid time input.")
    
    if len(digits) < 3:
        raise ValueError("Too short for a valid time.")

    # Always interpret last two digits as hundredths
    hundredths = digits[-2:]
    remaining = digits[:-2]
    seconds = remaining[-2:] if len(remaining) >= 2 else remaining
    minutes = remaining[:-2] if len(remaining) > 2 else '0'

    return f"00:{int(minutes):02}:{int(seconds):02}.{int(hundredths):02}"


def manualEntryPrompt():
    print("\nEntering Manual Entry Mode.\n")
    print("Type 'q' at any prompt to quit, or 'r' to restart your current entry.")
    print("Prefix name or event with '*' to persist across entries.")
    print("Example: '*John Doe' will persist name, which can be auto-entered if an input is left blank.\n")

    persistent_name = None
    persistent_event = None

    while True:
        name = input("Manual Entry - Enter swimmer's name: ").strip()
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
        
        if len(matches) == 0:
            print(f"No swimmer found matching: {name}")
            division = input("Enter division (e.g., 3B): ").strip().upper()
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

        event = input("Enter event (e.g., 100FR): ").strip().upper()
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

        raw_time = input("Enter time (e.g., 14256 or 1:42.56): ").strip()
        if raw_time.lower() == 'q':
            break

        try:
            formatted_time = smartTimeFormat(raw_time)

            # Read data
            timeCSV = readCSV(csv_output_file_name)
            swimmerList = getSwimmerList(swimmer_info_file_name)

            # Add swimmer if missing
            swimmerList.append([name, division])
            timeCSV = cleanUpCSV(swimmerList, timeCSV)

            # Find event index
            try:
                event_index = timeCSV[0].index(event)
            except ValueError:
                raise Exception(f"Event '{event}' not found in CSV header.")

            # Find or add swimmer row
            row_found = False
            for row in timeCSV:
                if row[0] == name:
                    row_found = True
                    existing_time = row[event_index]
                    break

            if not row_found:
                raise Exception(f"Swimmer {name} not found in timeCSV after cleanUpCSV.")

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
\t5. Relay maker (make_medley_relay.py)
\t6. Exit
"""

pdf_folder_name = "grabbed_pdfs"
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
            mode = int(mode)
        except Exception as e:
            print(f"Did not recognize input as number. Error: {e}")
            return
        if not(1 <= mode <= 6):
            print("Number is not in options.")
            continue
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
                medley_main()
            case 6:
                print("Exiting program.")
                return
            case _:
                print("Unexpected error, exiting program.")
                return
        print()

if __name__ == "__main__":
    main()