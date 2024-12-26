import rtmidi
import time
import pygame
import pygame.midi

# Constants
SCREEN_WIDTH = 800  # Width for pitch mapping
SCREEN_HEIGHT = 600  # Height for time looping (8 seconds)
PITCH_MIN = 36  # Minimum MIDI pitch to display
PITCH_MAX = 84  # Maximum MIDI pitch to display
TIME_LOOP = 8  # Loop duration in seconds
NOTE_COLORS = [(255, 0, 0), (255, 255, 0), (0, 0, 255)]  # Red, Yellow, Blue

def setup_midi_output():
    pygame.midi.init()
    return pygame.midi.Output(pygame.midi.get_default_output_id())

def play_note(midi_output, pitch, velocity):
    if velocity > 0:
        midi_output.note_on(pitch, velocity)
    else:
        midi_output.note_off(pitch)

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("MIDI Visualizer with Persistent Notes")

    midi_in = rtmidi.MidiIn()
    midi_output = setup_midi_output()
    available_ports = midi_in.get_ports()

    if not available_ports:
        print("No MIDI devices connected.")
        return

    # Open the second to last connected device
    latest_device_index = len(available_ports) - 2
    midi_in.open_port(latest_device_index)
    print(f"Connected to device: {available_ports[latest_device_index]}")

    # List to keep track of drawn notes as persistent "trails"
    drawn_notes = []
    last_loop_time = time.time()

    start_time = time.time()

    try:
        while True:
            current_time = time.time() - start_time
            looped_time = current_time % TIME_LOOP  # Wrap time into an 8-second loop
            loop_reset = int(current_time / TIME_LOOP)  # Detect loop reset for color change

            # Update color every time the loop resets (not during the loop)
            if loop_reset != last_loop_time:
                last_loop_time = loop_reset
                color_index = loop_reset % len(NOTE_COLORS)

            # Event handling for window close
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

            # Process incoming MIDI messages
            msg = midi_in.get_message()
            if msg:
                message, delta_time = msg
                status, pitch, velocity = message

                # Play or stop the note based on Note On/Off status
                if status == 144 and velocity > 0:  # Note On
                    play_note(midi_output, pitch, velocity)
                    # Calculate x and y for the note based on pitch and time
                    x = int(((pitch - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)) * SCREEN_WIDTH)
                    y = int((looped_time / TIME_LOOP) * SCREEN_HEIGHT)
                    # Save position, color index, and pitch to drawn_notes list (for persistent notes)
                    drawn_notes.append((x, y, color_index, pitch, loop_reset))
                elif status == 128 or (status == 144 and velocity == 0):  # Note Off
                    play_note(midi_output, pitch, 0)
                    # No removal of notes, only updating color on loop reset

            # Clear and update the screen
            screen.fill((0, 0, 0))

            # Draw all persistent notes from the drawn_notes list
            for x, y, color_index, pitch, last_reset in drawn_notes:
                # Only update color for notes that have been sustained and loop reset
                color = NOTE_COLORS[color_index]  # Get color based on the color index
                pygame.draw.circle(screen, color, (x, y), 5)

            # Draw the time marker line
            time_marker_y = int((looped_time / TIME_LOOP) * SCREEN_HEIGHT)
            pygame.draw.line(screen, (0, 255, 0), (0, time_marker_y), (SCREEN_WIDTH, time_marker_y), 2)

            pygame.display.flip()
            pygame.time.delay(10)  # Small delay to limit loop frequency

    except KeyboardInterrupt:
        print("Exiting.")
    finally:
        midi_in.close_port()
        midi_output.close()
        pygame.midi.quit()
        pygame.quit()

if __name__ == "__main__":
    main()
