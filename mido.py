import rtmidi
import time
import pygame
import pygame.midi

SCREEN_WIDTH = 1280  # Width for pitch mapping
SCREEN_HEIGHT = 720  # Height for time looping (8 seconds)
DIMENSIONS = (SCREEN_WIDTH, SCREEN_HEIGHT)
FULL_SCREEN = pygame.Rect((0, 0), DIMENSIONS)
PITCH_MIN = 36  # Minimum MIDI pitch to display
PITCH_MAX = 84  # Maximum MIDI pitch to display
KEY_WIDTH = SCREEN_WIDTH / (PITCH_MAX - PITCH_MIN)
TIME_LOOP = 8  # Loop duration in seconds
BLACK_KEYS = (1,3,6,8,10)

SKIN_TONE = ((233, 162, 74))
WHITE = ((255,255,255))
BROWN = ((97, 34, 16))
YELLOW = ((247, 253, 23))
SKY = ((65,200,253))
NOTE_COLORS = [(255, 3, 5), SKIN_TONE, (16, 68, 126), BROWN, YELLOW, (0,0,0)]
LINE_WIDTH = 4

def setup_midi_output():
    pygame.midi.init()
    return pygame.midi.Output(pygame.midi.get_default_output_id())

def play_note(midi_output, pitch, velocity):
    if velocity > 0:
        midi_output.note_on(pitch, velocity)
    else:
        midi_output.note_off(pitch)

def play_special_note(midi_output, pitch, velocity= 50):
    midi_output.set_instrument(5)
    play_note(midi_output, pitch, velocity)
    midi_output.set_instrument(0)

def main():
    pygame.init()
    screen = pygame.display.set_mode(DIMENSIONS)
    pygame.display.set_caption("MIDI Visualizer with Persistent Notes")

    midi_in = rtmidi.MidiIn()
    midi_output = setup_midi_output()
    available_ports = midi_in.get_ports()

    if not available_ports:
        print("No MIDI devices connected.")
        return

    # Open the second-to-last connected device
    # Novation LaunchKey 49 connects as 2 MIDI devices, so we use the first one
    latest_device_index = len(available_ports) - 2
    midi_in.open_port(latest_device_index)
    print(f"Connected to device: {available_ports[latest_device_index]}")

    # List to keep track of drawn notes as persistent "trails"
    drawn_notes = [] # List
    held_notes = {} # Set

    color_index = 0
    draw_background(screen)
    background_image = screen.copy()

    clock = pygame.time.Clock()
    max_height = radiusFromVelocity(128) * 2

    pause_time = -1
    
    last_loop_time = time.time()
    start_time = time.time()
    current_time = 0

    try:
        while True:
            # current_time = time.time() - start_time
            if (pause_time == -1):
                current_time += 2/60
            looped_time = current_time % TIME_LOOP  # Wrap time into an 8-second loop
            time_to_reset = int(current_time / TIME_LOOP)  # Detect loop reset for color change

            # Change the color every time the loop resets (every 8 seconds)
            if time_to_reset != last_loop_time:
                last_loop_time = time_to_reset
                color_index = (color_index + 1) % len(NOTE_COLORS)
                midi_output.note_off(43)
                midi_output.note_off(88)

            if looped_time == 0:
                # Save the background and reset the list of current notes
                refresh_whole_screen(screen, background_image)
                background_image = screen.copy()
                # Update the whole screen just once
                drawn_notes = []

            # COMMANDS
            for event in pygame.event.get():
                # End Program
                if event.type == pygame.QUIT:
                    return
                # Change Color
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    last_loop_time = time_to_reset
                    color_index = (color_index + 1) % len(NOTE_COLORS)
                    play_special_note(midi_output, 88)
                elif event.type == pygame.KEYDOWN:
                    # Clear Screen
                    if event.key == pygame.K_e:
                        drawn_notes = []
                        # background_image = pygame.Surface(DIMENSIONS)
                        draw_background(screen)
                        background_image = screen.copy()
                        refresh_whole_screen(screen, background_image)
                        play_special_note(midi_output, 43, 100)
                    # Pause Movement
                    elif event.key == pygame.K_LSHIFT:
                        pause_time = looped_time
                        refresh_whole_screen(screen, background_image)
                        play_special_note(midi_output, 76, 30)
                    # Undo Button
                    elif event.key == pygame.K_z:
                        if (len(drawn_notes) != 0):
                            note_removed = drawn_notes.pop()
                            # iterate backwards to find all notes that have
                            # the same pitch and close to the same time
                            i = len(drawn_notes) -1
                            while i > -1:
                                note = drawn_notes[i]
                                if (note[3] == note_removed[3] and note[1] + 6 > note_removed[1]):
                                    note_removed = drawn_notes.pop(i)
                                i -= 1
                            refresh_whole_screen(screen, background_image)
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_LSHIFT:
                        pause_time = -1
                        refresh_whole_screen(screen, background_image)
                        play_special_note(midi_output, 72, 30)

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

            if (pause_time != -1):
                looped_time = pause_time

            marker_y = int((looped_time / TIME_LOOP) * SCREEN_HEIGHT)
            screen_section = pygame.Rect(0, max(0, marker_y - max_height // 2), SCREEN_WIDTH, max_height)
            screen.blit(background_image, FULL_SCREEN, FULL_SCREEN)

            # Add all held notes to the drawn notes at the y-level in which they are pressed
            for pitch in held_notes:
                x = int(((pitch - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)) * SCREEN_WIDTH)
                drawn_notes.append((x, marker_y, color_index, pitch, held_notes.get(pitch), time_to_reset))

            # Draw all persistent notes from the drawn_notes list
            for x, y, one_color_index, pitch, velocity, last_reset in drawn_notes:
                # Only update color for notes that have been sustained and loop reset
                color = NOTE_COLORS[one_color_index]  # Get color based on the color index
                # if (y != marker_y):
                pygame.draw.circle(screen, color, (x, y), radiusFromVelocity(velocity))

            time_marker_y = int((looped_time / TIME_LOOP) * SCREEN_HEIGHT)

            # Outline all held notes (blends them together)
            for pitch in held_notes:
                x = int(((pitch - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)) * SCREEN_WIDTH)
                # draw outline only for currently held notes on the marker line
                pygame.draw.circle(screen, WHITE, (x, marker_y), radiusFromVelocity(held_notes.get(pitch)))


            # Draw the time marker line
            if time_marker_y < SCREEN_HEIGHT -2:
                # pygame.draw.line(screen, NOTE_COLORS[color_index], (0, time_marker_y), (SCREEN_WIDTH, time_marker_y), LINE_WIDTH)
                pygame.draw.line(screen, WHITE, (0, time_marker_y), (SCREEN_WIDTH, time_marker_y), LINE_WIDTH * 3)
                white = True
                for i in range(PITCH_MAX - PITCH_MIN):
                    start_pos = i * KEY_WIDTH - (KEY_WIDTH //2)
                    if((i%12) in BLACK_KEYS):
                        pygame.draw.line(screen, NOTE_COLORS[color_index], (start_pos + (KEY_WIDTH//2), time_marker_y - (LINE_WIDTH*1.5)), (start_pos + (KEY_WIDTH//2), time_marker_y + (LINE_WIDTH*1.5)), LINE_WIDTH)
                        pygame.draw.line(screen, NOTE_COLORS[color_index], (start_pos, time_marker_y - LINE_WIDTH), (start_pos + KEY_WIDTH, time_marker_y - LINE_WIDTH), LINE_WIDTH * 2)
                    elif (i%12 in (5,0)):
                        pygame.draw.line(screen, NOTE_COLORS[color_index], (start_pos, time_marker_y - (LINE_WIDTH*1.5)), (start_pos, time_marker_y + (LINE_WIDTH*1.5)), LINE_WIDTH)
            
            for pitch in held_notes:
                x = int(((pitch - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)) * SCREEN_WIDTH)
                # draw outline only for currently held notes on the marker line
                color = NOTE_COLORS[one_color_index]
                pygame.draw.circle(screen, color, (x, y), radiusFromVelocity(held_notes.get(pitch)) - LINE_WIDTH)
                
            # Draw held notes as darkened key notes
            for pitch in held_notes:
                x = int(((pitch - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)) * SCREEN_WIDTH)
                # draw outline only for currently held notes on the marker line
                color = (NOTE_COLORS[one_color_index])
                color = (max(0,color[0]-50),max(0,color[1]-50),max(0,color[2]-50))
                pygame.draw.rect(screen, color, ((x - (KEY_WIDTH), time_marker_y - (LINE_WIDTH*3)),(KEY_WIDTH*2 + LINE_WIDTH//2, (LINE_WIDTH * 6))),
                                 border_radius=16)

                # Decrease the pitch over time
                velocity = held_notes.get(pitch)
                # held_notes.update({pitch: max(0, (velocity -.1 - 10000/max(1,pow(velocity,3))))})
                held_notes.update({pitch: max(0, velocity*.994 - (5/max(1,velocity)))})


            # Draw the hint for the next colors at the end of it
            hint = 16
            pygame.draw.circle(screen, NOTE_COLORS[(color_index + 2)%len(NOTE_COLORS)], (SCREEN_WIDTH - (hint*.2), time_marker_y), hint * .5)
            pygame.draw.circle(screen, NOTE_COLORS[(color_index + 1)%len(NOTE_COLORS)], (SCREEN_WIDTH - (hint* 1.05), time_marker_y), hint * .72)
            pygame.draw.circle(screen, NOTE_COLORS[(color_index)], (SCREEN_WIDTH - (hint* 2.15), time_marker_y), hint)

            # flip to newly drawn display
            pygame.display.flip()
            clock.tick(30)

    except KeyboardInterrupt:
        print("Exiting.")

    finally:
        midi_in.close_port()
        midi_output.close()
        pygame.midi.quit()
        pygame.quit()

def radiusFromVelocity(v):
    """give a number from 1 to 127"""
    # return v * v * .007
    # return (pow(v - 70,3)/17150) + (.5*v) + 20
    return (pow(v-50,3)/7600) + (.316*v) + 17

def refresh_whole_screen(screen, background_image):
    # screen.blit(background_image, (0,0), FULL_SCREEN)
    # pygame.display.update(FULL_SCREEN)
    # pygame.display.flip()
    pass

def draw_background(screen):
    pygame.draw.rect(screen, SKY, FULL_SCREEN)

if __name__ == "__main__":
    main()
