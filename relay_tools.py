import csv
import os
import itertools
from time import perf_counter_ns as time

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
    # 1. Create relay by name
    # 2. Create relay by division
    # 3. Estimate relay time (names only)
    
    mode_prompt = """Choose a mode:
        1. Make ideal relay - name
        2. Make ideal relay - division
        3. Estimate relay time
        Q. Quit\n"""
    mode = input(mode_prompt).strip()

    match mode:
        case '1' | '2' | '3':
            return int(mode)
        
        case '' | 'q' | 'quit':
            print("Exiting mode selection.")
            return None
        case _:
            print("Invalid mode selected.")
            return 0

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
        
        elif div in ["Q", "QUIT"]:
            print("Quiting division selection.")
            return None
        
        else:
            print(f"Invalid division: {div}")
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
        if fifty_time and not (
            (# Div 4+ and O2 swimmers cannot swim 50 BR or 50 BK
                (
                    len(csvtimes[swimmer_index][1]) == 2 and int(csvtimes[swimmer_index][1][0]) > 3  # Div 4+
                    or len(csvtimes[swimmer_index][1]) == 3 and int(csvtimes[swimmer_index][1][1]) == 2  # O2
                )
                and (stroke == 'BR' or stroke == 'BK')
            )):
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

def name_fuzzy_search(name, csvnames):
    # Build list of candidate names
    name_list = [entry for entry in csvnames if entry[0]]
    name_lower = name.lower()
    
    # Try to match exact names first
    exact_matches = [candidate for candidate in name_list if candidate[0].lower() == name_lower]
    if exact_matches:
        return [exact_matches[0]]

    # Try to match as a substring (allows partial input matches)
    partial_matches = [candidate for candidate in name_list if name_lower in candidate[0].lower()]
    if partial_matches:
        return sorted(partial_matches)

    # Fallback to fuzzy search using Levenshtein distance
    matches = []
    threshold = max(1, len(name_lower) // 3)  # Set a threshold based on the length of the input name
    # Iterate through candidates and calculate Levenshtein distance
    for candidate in name_list:
        candidate_lower = candidate[0].lower()
        min_distance = float('inf')
        # Slide a window over candidate to compare to the input
        if len(candidate_lower) >= len(name_lower):
            for i in range(len(candidate_lower) - len(name_lower) + 1):
                window = candidate_lower[i:i+len(name_lower)]
                d = levenshtein_distance(name_lower, window)
                if d < min_distance:
                    min_distance = d
        else:
            min_distance = levenshtein_distance(name_lower, candidate_lower)
        if min_distance <= threshold:
            matches.append((min_distance, candidate))
    
    return [[candidate[0], candidate[1]] for _, candidate in sorted(matches, key=lambda x: x[0])]

def choose_names(csvtimes, input_mode, min_names=0, max_names=float('inf')):
    names = []
    
    if input_mode not in [1, 2, 3]:
        raise ValueError("Invalid input mode for choosing names. (Internal error, should not happen)")
    if min_names < 0 or max_names < min_names:
        raise ValueError("Invalid minimum or maximum number of names specified.")
    
    if input_mode in [1, 2]:
        input_prompt = "IDEAL RELAY - Enter a name (leave blank to finish): "
    elif input_mode in [3]:
        input_prompt = "RELAY TIME - Enter a name (leave blank to finish): "
    else:
        raise ValueError("Invalid input mode for choosing names. (Internal error, should not happen)")
    
    while len(names) < max_names:
        name = input("\n" + input_prompt).strip()
        if not name:
            break
        possible_matches = [match[0] for match in name_fuzzy_search(name, csvtimes)]
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
    if len(names) < min_names:
        print(f"Not enough swimmers selected. At least {min_names} swimmers are required.")
        return None
    
    seen = set()
    return [name for name in names if not (name in seen or seen.add(name))]  # Remove duplicates

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

def find_best_combo(times, relay_type):
    # Minimum number of swimmers is 4, one for each stroke.
    if len(times) < 4:
        print("Not enough swimmers to form a relay team. At least 4 swimmers are required.")
        return
    
    # Convert string times to float values.    
    for i in range(len(times)):
        times[i] = (times[i][0], [durationToTime(t) if t else None for t in times[i][1]])
    
    if relay_type == "medley":
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
            
            print("\nBest medley relay combination:")
            # print(list(zip(output_strokes, ordered_choice)))
            for stroke in output_strokes:
                idx = default_strokes.index(stroke)
                row_index, time_value = best_choice[idx]
                swimmer_name = times[row_index][0]
                print(f"{stroke}: {swimmer_name}, time {timeToDuration(time_value)}")
            print(f"\nTotal relay time: {timeToDuration(min_sum)}")
    else:
        # For freestyle, we just need to sort by the freestyle times.
        free_times = [(entry[0], entry[1][3]) for entry in times]  # Get only the freestyle times
        free_times = [entry for entry in free_times if entry[1] is not None]  # Filter out None values
        if len(free_times) < 4:
            print("Not enough swimmers with valid freestyle times to form a relay team.")
            return
        # Sort by freestyle time
        free_times.sort(key=lambda x: x[1])
        free_times.insert(3, free_times.pop(0))  # Move the fastest swimmer to the end (4th position)
        print("\nBest freestyle relay combination:")
        for swimmer, time in free_times[:4]:  # Take the top 4 swimmers
            print(f"FREE: {swimmer}, time {timeToDuration(time)}")
        print(f"\nTotal relay time: {timeToDuration(sum(i[1] for i in free_times[:4]))}")

def get_type_of_relay(mode):
    if mode in [3]:
        mode_prompt = """
            Type of relay to TEST:
            1. Medley Relay
            2. Freestyle Relay\n"""
    elif mode in [1, 2]:
        mode_prompt = """
            Type of relay to MAKE:
            1. Medley Relay
            2. Freestyle Relay\n"""
    else:
        raise ValueError("Mode selected is not recognized for relay type selection. (Internal error)")
    
    relay_type = input(mode_prompt).strip().lower()
    match relay_type:
        case '1' | 'm' | 'medley':
            return "medley"
        case '2' | 'f' | 'freestyle':
            return "freestyle"
        case '' | 'q' | 'quit':
            print("Exiting.")
            return None
        case _:
            print("Invalid relay type selected.")
            return 0

def calc_medley_time(times):
    strokes = ["BACK", "BREAST", "FLY", "FREE"]
    if not times or len(times) != 4:
        raise ValueError("Invalid input: times must be a list of 4 tuples (swimmer, [times])")
    
    for i in range(len(times)):
        times[i] = (times[i][0], [durationToTime(t) if t else None for t in times[i][1]])
    
    times_needed = [
        (times[0][0], times[0][1][1]),  # Backstroke
        (times[1][0], times[1][1][2]),  # Breaststroke
        (times[2][0], times[2][1][0]),  # Butterfly
        (times[3][0], times[3][1][3])   # Freestyle
    ]
    
    print("\nMedley Relay Swimmers and their times:")
    for i in range(len(times_needed)):
        swimmer, time = times_needed[i]
        if time is not None:
            print(f"{strokes[i]}: {swimmer}, time {timeToDuration(time)}")
        else:
            print(f"{strokes[i]}: {swimmer} does not have a valid time.")
            return None
    
    return sum([t[1] for t in times_needed if t[1] is not None])

def calc_freestyle_time(times):
    if not times or len(times) != 4:
        raise ValueError("Invalid input: times must be a list of 4 tuples (swimmer, [times])")
    
    for i in range(len(times)):
        times[i] = (times[i][0], [durationToTime(t) if t else None for t in times[i][1]])
    
    freestyle_times = [(times[i][0], times[i][1][3]) for i in range(4)]
    
    print("\nFreestyle Relay Swimmers and their times:")
    for swimmer, time in freestyle_times:
        if time is not None:
            print(f"FREE: {swimmer}, time {timeToDuration(time)}")
        else:
            print(f"{swimmer} does not have a valid time.")
            return None
    
    return sum(t[1] for t in freestyle_times if t[1] is not None)

def relay_time(times, mode):
    match mode:
        case "medley":
            time = calc_medley_time(times)
            if time is not None:
                print(f"\nEstimated Medley Relay time: {timeToDuration(time)}")
        case "freestyle":
            time = calc_freestyle_time(times)
            if time is not None:
                print(f"\nEstimated Freestyle Relay time: {timeToDuration(time)}")
        case 0:
            print("Invalid relay type selected. Please try again.")
        case None:
            print("Exiting relay type selection.")
            return None
        case _:
            print("IMPOSSIBLE ERROR: Relay mode (tester) not recognized.")
            return None
    return 1

def medley_main():
    csvdata = read_times(best_time_file)
    if not csvdata:
        print("No times found in the best time sheet.")
        return
    
    print("Welcome to the Relay Maker!")
    while True:
        
        input_mode = choose_mode()
        
        match input_mode:
            case 0:
                print("Invalid mode selected. Please try again.")
                continue
            case 1:
                names = choose_names(csvdata, input_mode)
                if not names:
                    continue
                times = get_swimtimes_byname(names, csvdata)
            case 2:
                divs = choose_divisions()
                if not divs:
                    continue
                times = get_swimtimes_bydiv(divs, csvdata)
            case 3:
                names = choose_names(csvdata, input_mode, min_names=4, max_names=4)
                if not names:
                    continue
                times = get_swimtimes_byname(names, csvdata)
            case None:
                print("Exiting the Relay Maker.")
                return 1
            case _:
                return
        
        if not times:
            print("No valid times found for the selected swimmers.")
            continue
        
        print("\nSelected swimmers and their times:")
        max_name_length = max(len(swimmer[0]) for swimmer in times)
        for swimmer, swimmer_times in times:
            print(f"{swimmer}:{' '*max(1, max_name_length-len(swimmer)+1)}{'\t'.join([t if t is not None else 8*' '+'N/A' for t in swimmer_times])}")
            # print(f"{swimmer}: {'\t'.join([t for t in swimmer_times if t is not None else 'None'])}")
        
        relay_type = get_type_of_relay(input_mode)
        
        st = time()
        match input_mode:
            case 1 | 2:
                find_best_combo(times, relay_type)
            case 3:
                if not(relay_time(times, relay_type)):
                    continue
            case _:
                print("Theoretically impossible error: mode not recognized.")
        nd = time()
        print(f"\nTook {(nd - st) / 1_000_000} ms to determine.")
        return


if __name__ == "__main__":
    while medley_main() is None:
        continue