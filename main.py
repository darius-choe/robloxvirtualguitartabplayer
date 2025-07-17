import guitarpro
from pynput.keyboard import Key, Controller
import time
import sys
from collections import defaultdict
import tkinter as tk
from tkinter import filedialog
import os

# Keyboard key mappings for each string (frets 0 to 12)
string_key_rows = {
    1: ['~', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '+'],  # High E (shift required)
    2: ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\\'],      # B (shift required)
    3: ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '='],       # G (no shift)
    4: ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\\'],      # D (no shift)
    5: ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'", "'"],            # A (no shift; handle fret 12 manually)
    6: ['z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', 'left', 'right', '?'], # Low E (no shift)
}

strings_requiring_shift = {1, 2}
keyboard = Controller()

def parse_selected_track(track):
    notes = []
    tuning = [string.value for string in track.strings]

    for measure in track.measures:
        current_tick = measure.start

        for voice in measure.voices:
            for beat in voice.beats:
                if not beat.notes:
                    current_tick += beat.duration.time
                    continue

                duration = beat.duration.time
                beat_tick = current_tick

                for note in beat.notes:
                    effect = note.effect
                    if getattr(effect, 'palmMute', False) or getattr(effect, 'deadNote', False):
                        continue

                    original_string = note.string
                    original_fret = note.value
                    original_pitch = tuning[original_string - 1] + original_fret

                    found = False

                    for s in range(1, 7):
                        string_pitch = tuning[s - 1]
                        candidate_fret = original_pitch - string_pitch
                        if 0 <= candidate_fret <= 12:
                            slide = getattr(effect, 'slideTo', None) or getattr(effect, 'slideFrom', None)
                            notes.append((beat_tick, s, candidate_fret, duration, bool(slide)))
                            found = True
                            break

                    if not found:
                        original_pitch -= 12
                        for s in range(1, 7):
                            string_pitch = tuning[s - 1]
                            candidate_fret = original_pitch - string_pitch
                            if 0 <= candidate_fret <= 12:
                                slide = getattr(effect, 'slideTo', None) or getattr(effect, 'slideFrom', None)
                                notes.append((beat_tick, s, candidate_fret, duration, bool(slide)))
                                found = True
                                break

                    if not found:
                        print(f"Skipping: string {original_string}, fret {original_fret} (unplayable in 0–12 range)")

                current_tick += duration

    return notes

def press_note(string, fret):
    if string == 5 and fret == 12:
        keyboard.press(Key.shift)
        keyboard.press("'")
        keyboard.release("'")
        keyboard.release(Key.shift)
        return

    if string not in string_key_rows:
        print(f"Skipping: string {string}, fret {fret} (string not mapped)")
        return
    if fret >= len(string_key_rows[string]):
        print(f"No key assigned for string {string}, fret {fret}")
        return

    key = string_key_rows[string][fret]
    if key == '':
        print(f"No key assigned for string {string}, fret {fret}")
        return

    if string == 6 and key in ['left', 'right', '?']:
        keyboard.press(getattr(Key, key) if key in ['left', 'right'] else key)
        keyboard.release(getattr(Key, key) if key in ['left', 'right'] else key)
        return

    if string in strings_requiring_shift:
        keyboard.press(Key.shift)
        keyboard.press(key)
        keyboard.release(key)
        keyboard.release(Key.shift)
    else:
        keyboard.press(key)
        keyboard.release(key)

def group_notes_by_start(notes):
    grouped = defaultdict(list)
    for start_tick, string, fret, duration, slide in notes:
        grouped[start_tick].append((string, fret, duration, slide))
    return grouped

def play_tab(notes, bpm):
    beat_duration_sec = 60 / bpm
    tick_unit = beat_duration_sec / 960

    grouped_notes = group_notes_by_start(notes)
    sorted_starts = sorted(grouped_notes.keys())

    for i, start in enumerate(sorted_starts):
        chord_notes = grouped_notes[start]

        for string, fret, duration, slide in chord_notes:
            press_note(string, fret)

        if i + 1 < len(sorted_starts):
            wait_ticks = sorted_starts[i + 1] - start
        else:
            wait_ticks = max(note[2] for note in chord_notes)

        time.sleep(wait_ticks * tick_unit)

if __name__ == "__main__":
    # Open file picker, default to Downloads
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select a Guitar Pro file",
        initialdir=downloads_path,
        filetypes=[("Guitar Pro files", "*.gp5 *.gpx *.gp4 *.gp3"), ("All files", "*.*")]
    )

    if not file_path:
        print("No file selected. Exiting.")
        sys.exit()

    print(f"Loading {file_path}...")
    song = guitarpro.parse(file_path)

    print("\nAvailable tracks:")
    for i, track in enumerate(song.tracks):
        print(f"{i + 1}: {track.name}")

    while True:
        try:
            choice = int(input("Select a track number: ")) - 1
            if 0 <= choice < len(song.tracks):
                selected_track = song.tracks[choice]
                break
            else:
                print("Invalid track number.")
        except ValueError:
            print("Please enter a valid number.")

    notes = parse_selected_track(selected_track)
    default_bpm = song.tempo
    print(f"\nFound {len(notes)} playable notes. Default BPM from file: {default_bpm}")

    use_default = input("Use default BPM from file? (Y/N): ").strip().lower()
    if use_default == 'y':
        bpm = default_bpm
    else:
        while True:
            try:
                bpm = int(input("Enter BPM: "))
                break
            except ValueError:
                print("Invalid number, try again.")

    print("Switch to Roblox or game window now. Starting in 3 seconds...")
    time.sleep(3)
    play_tab(notes, bpm)
