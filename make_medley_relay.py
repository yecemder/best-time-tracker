import csv
import os
import itertools

best_time_file = "master_times.csv"

def read_times(file_path):
    times = []
    if not os.path.exists(file_path):
        raise Exception(f"File not found: {file_path}")

    with open(file_path, mode='r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            times.append(row)
    
    return times

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
    
    return round(total, 2)

def timeToDuration(time: float) -> str:
    if not isinstance(time, (float, int)):
        raise TypeError("time must be a float or int")
    if time < 0:
        raise Exception(f"Attempted to convert invalid time to duration: {time}")
    if time == 0:
        return "00:00:00.00"
    time = round(time, 2)
    hours = int(time // 3600)
    time %= 3600
    minutes = int(time // 60)
    seconds = int(time % 60)
    dd = round(round(time - int(time), 2)*100)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{dd:02}"

def choose_mode():
    # TRUE = Swimmers by Div, FALSE = Swimmers by Name
    mode_prompt = "Choose mode:\n\t1. Swimmers by DIV\n\t2. Swimmers by NAME\n"
    mode = input(mode_prompt).strip()

    if mode == "1":
        return True
    elif mode == "2":
        return False
    else:
        print("Invalid mode selected.")
        return None

def choose_divisions():
    divs = input("Which divisions would you like to include? (separate with spaces)\n").strip().upper().split()
    print()
    if len(divs) == 0:
        print("Invalid divisions given.")
        return choose_divisions()
    s_div_nums = [str(i) for i in range(1, 9)]
    o_div_nums = ["1", "2"]
    allowed_genders = ["G", "B"]
    for div in divs:
        if len(div) == 2:
            if not(div[0] in s_div_nums and div[1] in allowed_genders):
                print(f"Invalid S division: {div}")
                return choose_divisions()
        
        elif len(div) == 3:
            if not(div[0] == "O" and div[1] in o_div_nums and div[2] in allowed_genders):
                print(f"Invalid O division: {div}")
                return choose_divisions()
        
        else:
            print(f"Invalid division format: {div}")
            return choose_divisions()
    return divs

def hundred_to_fifty(time):
    return timeToDuration(0.591428 * (durationToTime(time) ** 0.931986))

def get_swimmer_times(swimmer_name, csvtimes):
    # Find swimmer in CSV
    swimmer_index = 0
    for row_ind in range(len(csvtimes)):
        if csvtimes[row_ind][0].lower() == swimmer_name.lower():
            swimmer_index = row_ind
            break
    else:
        raise Exception(f"get_swimmer_times() couldn't find swimmer: {swimmer_name}")

    key = ['Name','Div.','100IM','200IM','50FL','100FL','50BK','100BK','50BR','100BR','50FR','100FR']
    swimmer_times : list[str | None] = [None] * 4

    for i, stroke in enumerate(['FL', 'BK', 'BR', 'FR']):
        # Get 50 time if it exists
        fifty_time = csvtimes[swimmer_index][key.index(f'50{stroke}')]
        if fifty_time:
            swimmer_times[i] = fifty_time
        else:
            # If 50 time doesn't exist, get 100 time and divide by 2
            hundred_time = csvtimes[swimmer_index][key.index(f'100{stroke}')]
            if hundred_time:
                swimmer_times[i] = hundred_to_fifty(hundred_time)

    return swimmer_times

def get_swimtimes_bydiv(divs, csvtimes):
    swimmer_names = []
    for entry in csvtimes:
        if (entry[1] in divs) and (entry[0] not in swimmer_names) and (entry[0]):
            # Get names that match division list, avoiding duplicates
            swimmer_names.append(entry[0])

    return get_swimtimes_byname(swimmer_names, csvtimes)

def get_swimtimes_byname(names, csvtimes):
    swimmers = []
    for name in names:
        try:
            swimmer_times = get_swimmer_times(name, csvtimes)
            swimmers.append((name, swimmer_times))
        except Exception as e:
            print(e)
    return swimmers

def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def name_fuzzy_search(name, csvtimes):
    # Build list of candidate names
    name_list = [entry[0] for entry in csvtimes if entry[0]]
    name_lower = name.lower()
    
    # Try to match exact names first
    exact_matches = [candidate for candidate in name_list if candidate.lower() == name_lower]
    if exact_matches:
        return exact_matches

    # Try to match as a substring (allows partial input matches)
    partial_matches = [candidate for candidate in name_list if name_lower in candidate.lower()]
    if partial_matches:
        return sorted(partial_matches)

    # Fallback to fuzzy search using Levenshtein distance
    matches = []
    threshold = 2
    for candidate in name_list:
        distance = levenshtein_distance(name_lower, candidate.lower())
        if distance <= threshold:
            matches.append((distance, candidate))
    
    return [candidate for _, candidate in sorted(matches, key=lambda x: x[0])]

def choose_names(csvtimes):
    names = []
    while True:
        name = input("\nEnter a swimmer's name (leave blank to finish): ").strip()
        if not name:
            break
        possible_matches = name_fuzzy_search(name, csvtimes)
        if possible_matches:
            if len(possible_matches) == 1:
                names.append(possible_matches[0])
                print(f"Added swimmer: {possible_matches[0]}")
            else:
                print("\nPossible matches:")
                for i, match in enumerate(possible_matches):
                    print(f"{i + 1}. {match}")
                choice = input("Select a swimmer by number or type '(c)ancel' to try again: ").strip()
                if choice.lower() in ['cancel', 'c']:
                    continue
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(possible_matches):
                        names.append(possible_matches[index])
                        print(f"Added swimmer: {possible_matches[index]}")
                        continue
                    else:
                        print("Invalid selection. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number or 'cancel'.")
        else:
            print("No matches found. Please try again.")
    
    return list(set(names))  # Remove duplicates

def find_minimum_sum_combination(times):
    # 'times' is a list of tuples: (name, [float values])
    if not times:
        return None, None

    # Extract the list of float values from each entry.
    time_lists = [entry[1] for entry in times]
    cols = len(time_lists[0])
    
    # Verify that each entry has the same number of float columns.
    if not all(len(t) == cols for t in time_lists):
        print("All rows must have the same number of float columns.")
        exit(1)
        
    rows = len(times)
    
    # Build candidate lists for each column.
    candidates = []
    for j in range(cols):
        col_candidates = []
        for i in range(rows):
            value = time_lists[i][j]
            if value is not None:
                col_candidates.append((i, value))
        if not col_candidates:
            # If any column has no valid candidates, there is no valid combination.
            return None, None
        candidates.append(col_candidates)
    
    # Find the combination with the minimum total sum.
    best_choice = None
    min_sum = None
    for combo in itertools.product(*candidates):
        rows_used = [pair[0] for pair in combo]
        if len(set(rows_used)) != len(rows_used):
            continue
        current_sum = sum(pair[1] for pair in combo)
        if min_sum is None or current_sum < min_sum:
            min_sum = current_sum
            best_choice = combo

    return best_choice, min_sum

def find_best_combo(times):
    # Minimum number of swimmers is 4, one for each stroke.
    if len(times) < 4:
        print("Not enough swimmers to form a relay team. At least 4 swimmers are required.")
        return    
    
    # Convert string times to float values.    
    for i in range(len(times)):
        print(times[i])
        times[i] = (times[i][0], [durationToTime(t) if t else None for t in times[i][1]])
    
    
    # The default order in the input grid corresponds to these strokes:
    default_strokes = ["FLY", "BACK", "BREAST", "FREE"]
    # Specify desired output order here (e.g., ["BACK", "BREAST", "FLY", "FREE"])
    output_strokes = ["BACK", "BREAST", "FLY", "FREE"]

    best_choice, min_sum = find_minimum_sum_combination(times)
    
    if best_choice is None or min_sum is None:
        print("No valid combination exists (one stroke has no valid float values).")
        return
    else:
        # Reorder the chosen combination to match the desired output order.
        ordered_choice = []
        for stroke in output_strokes:
            idx = default_strokes.index(stroke)
            ordered_choice.append(best_choice[idx])
            
        print("\nBest relay combination:")
        # print(list(zip(output_strokes, ordered_choice)))
        for stroke in output_strokes:
            idx = default_strokes.index(stroke)
            row_index, time_value = best_choice[idx]
            swimmer_name = times[row_index][0]
            print(f"{stroke}: {swimmer_name}, time {timeToDuration(time_value)}")
        print(f"\nTotal relay time: {timeToDuration(min_sum)}")

def medley_main():
    csvdata = read_times(best_time_file)
    if not csvdata:
        print("No times found in the file.")
        return
    print("Welcome to the Relay Maker!")
    while True:
        
        mode = choose_mode()
        if mode is None:
            return
        
        if mode:
            divs = choose_divisions()
            if divs is None:
                continue
            times = get_swimtimes_bydiv(divs, csvdata)
        else:
            names = choose_names(csvdata)
            if not names:
                continue
            times = get_swimtimes_byname(names, csvdata)
        
        if not times:
            print("No valid times found for the selected swimmers.")
            continue
        
        print("\nSelected swimmers and their times:")
        for swimmer, swimmer_times in times:
            print(f"{swimmer}: {swimmer_times}")
        
        find_best_combo(times)
        return

if __name__ == "__main__":
    medley_main()

# print(get_swimtimes_bydiv(['3B'], times))
# print(get_swimtimes_byname(['Matthew Mizukami'], times))

# print(choose_names(times))