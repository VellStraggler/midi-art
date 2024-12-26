import rtmidi
import time
import pygame
import pygame.midi

# Constants
SCREEN_WIDTH = 1280  # Width for pitch mapping
SCREEN_HEIGHT = 720  # Height for time looping (8 seconds)
PITCH_MIN = 36  # Minimum MIDI pitch to display
PITCH_MAX = 84  # Maximum MIDI pitch to display
TIME_LOOP = 8  # Loop duration in seconds
NOTE_COLORS = [(255, 0, 0), (255, 255, 0), (0, 0, 255)]  # Red, Yellow, Blue
#NOTE_COLORS = [(107,190,155),(245, 244, 158),(201,119,200),(127,127,127)]
WHITE = ((255,255,255))
LINE_WIDTH = 4

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
    drawn_notes = [] # List
    held_notes = {} # Set

    last_loop_time = time.time()
    start_time = time.time()

    color_index = 0
    background_image = screen.copy()

    clock = pygame.time.Clock()
    max_height = radiusFromVelocity(128) * 2

    try:
        while True:
            current_time = time.time() - start_time
            looped_time = current_time % TIME_LOOP  # Wrap time into an 8-second loop
            loop_reset = int(current_time / TIME_LOOP)  # Detect loop reset for color change

            # Change the color every time the loop resets (every 8 seconds)
            if loop_reset != last_loop_time:
                last_loop_time = loop_reset
                color_index = loop_reset % len(NOTE_COLORS)

                # Save the background and reset the list of current notes
                background_image = screen.copy()
                # screen.blit(background_image, (0,0))
                # Update the whole screen just once
                drawn_notes = []


            # Event handling for window close
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

            # Process all incoming MIDI messages
            while True:
                msg = midi_in.get_message()
                if not msg:
                    break
                else:
                    message, delta_time = msg
                    status, pitch, velocity = message

                    # Play or stop the note based on Note On/Off status
                    if status == 144 and velocity > 0:  # Note On
                        play_note(midi_output, pitch, velocity)
                        # Calculate x and y for the note based on pitch and time
                        # Save position, color index, and pitch to drawn_notes list (for persistent notes)
                        held_notes[pitch] = velocity
                    elif status == 128:# or (status == 144 and velocity == 0):  # Note Off
                        play_note(midi_output, pitch, 0)
                        
                        if pitch in held_notes:
                            held_notes.pop(pitch)
                        # No removal of notes, only updating color on loop reset

            # Clear and update the screen with the known background image
            # Only update around the marker line up to the height of the largest possible circle
            marker_y = int((looped_time / TIME_LOOP) * SCREEN_HEIGHT)
            screen_section = pygame.Rect(0, max(0, marker_y - max_height // 2), SCREEN_WIDTH, max_height)
            screen.blit(background_image, screen_section, screen_section)

            # Add all held notes to the drawn notes at the y-level in which they are pressed
            for pitch in held_notes:
                x = int(((pitch - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)) * SCREEN_WIDTH)
                drawn_notes.append((x, marker_y, color_index, pitch, velocity, loop_reset))

            # Draw all persistent notes from the drawn_notes list
            for x, y, one_color_index, pitch, velocity, last_reset in drawn_notes:
                # Only update color for notes that have been sustained and loop reset
                color = NOTE_COLORS[one_color_index]  # Get color based on the color index
                # other_color = ((max(color[0]-50,0),max(color[1]-50,0),max(color[2]-50,0)))
                if (y != marker_y):
                    pygame.draw.circle(screen, color, (x, y), radiusFromVelocity(velocity))

            time_marker_y = int((looped_time / TIME_LOOP) * SCREEN_HEIGHT)
            
            # Outline marker line
            if (len(held_notes) != 0):
                pygame.draw.line(screen, WHITE, (0, time_marker_y), (SCREEN_WIDTH, time_marker_y), LINE_WIDTH * 3)

            # Outline all held notes (blends them together)
            for pitch in held_notes:
                x = int(((pitch - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)) * SCREEN_WIDTH)
                # draw outline only for currently held notes on the marker line
                pygame.draw.circle(screen, WHITE, (x, marker_y), radiusFromVelocity(velocity))

            # Draw all held notes
            for pitch in held_notes:
                x = int(((pitch - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)) * SCREEN_WIDTH)
                # draw outline only for currently held notes on the marker line
                color = NOTE_COLORS[one_color_index]
                pygame.draw.circle(screen, color, (x, y), radiusFromVelocity(velocity) - LINE_WIDTH)

            # Draw the time marker line
            pygame.draw.line(screen, NOTE_COLORS[color_index], (0, time_marker_y), (SCREEN_WIDTH, time_marker_y), LINE_WIDTH)

            # Draw the hint for the next colors at the end of it
            hint = 32
            pygame.draw.line(screen, NOTE_COLORS[(color_index + 1)%3], (SCREEN_WIDTH - (hint* 2), time_marker_y), (SCREEN_WIDTH, time_marker_y), LINE_WIDTH)
            pygame.draw.line(screen, NOTE_COLORS[(color_index + 2)%3], (SCREEN_WIDTH - hint, time_marker_y), (SCREEN_WIDTH, time_marker_y), LINE_WIDTH)

            # flip to newly drawn display
            # pygame.display.flip()
            pygame.display.update(screen_section)
            clock.tick(60)

    except KeyboardInterrupt:
        print("Exiting.")

    finally:
        midi_in.close_port()
        midi_output.close()
        pygame.midi.quit()
        pygame.quit()

def radiusFromVelocity(velocity):
    """give a number from 1 to 127"""
    return velocity * velocity * .008

if __name__ == "__main__":
    main()
